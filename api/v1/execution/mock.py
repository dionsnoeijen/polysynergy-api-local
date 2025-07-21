import inspect
import logging
import os
import time
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import JSONResponse
from polysynergy_node_runner.execution_context.send_flow_event import send_flow_event
from polysynergy_node_runner.services.active_listeners_service import (
    ActiveListenersService
)

from models import Project, NodeSetupVersion
from services.mock_sync_service import MockSyncService, get_mock_sync_service
from repositories.node_setup_repository import get_node_setup_repository, NodeSetupRepository
from services.active_listeners_service import get_active_listeners_service
from services.lambda_service import get_lambda_service, LambdaService
from utils.get_current_account import get_project_or_403
from core.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_RETRIES = 5
INITIAL_DELAY = 2

@router.get("/{version_id}/{mock_node_id}/", response_model=None)
async def mock_play(
    version_id: uuid.UUID,
    mock_node_id: uuid.UUID,
    sub_stage: str = Query("mock"),
    project: Project = Depends(get_project_or_403),
    active_listener_service: ActiveListenersService = Depends(get_active_listeners_service),
    lambda_service: LambdaService = Depends(get_lambda_service),
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
    mock_sync_service: MockSyncService = Depends(get_mock_sync_service)
):
    active_listener_service.set_listener(str(version_id))
    version = node_setup_repository.get_or_404(version_id)
    if settings.EXECUTE_NODE_SETUP_LOCAL:
        return await execute_local(project, version, mock_node_id, sub_stage, active_listener_service)

    function_name = f"node_setup_{version_id}_mock"
    mock_sync_service.sync_if_needed(version, project)
    payload = {
        "node_id": str(mock_node_id),
        "s3_key": f"{project.tenant_id}/{project.id}/{function_name}.py",
        "mock": True,
        "sub_stage": sub_stage,
    }

    delay = INITIAL_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = lambda_service.invoke_lambda(function_name, payload)
            return {"status": "mock executed", "result": response}
        except Exception as e:
            msg = str(e)
            if "ResourceConflictException" in msg and "Pending" in msg:
                logger.warning(f"Lambda pending, retry {attempt}/{MAX_RETRIES} in {delay}s")
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Lambda exec error: {msg}")
                raise HTTPException(status_code=500, detail={"error": "Lambda error", "details": msg})

    raise HTTPException(status_code=503, detail="Lambda remained in pending status")


async def execute_local(
    project: Project,
    version: NodeSetupVersion,
    mock_node_id: uuid.UUID,
    sub_stage: str,
    active_listener_service: ActiveListenersService
) -> dict | JSONResponse:
    os.environ['PROJECT_ID'] = str(project.id)
    os.environ['TENANT_ID'] = str(project.tenant_id)

    os.environ.setdefault("AWS_REGION", settings.AWS_REGION)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)

    os.environ.setdefault("PUBNUB_PUBLISH_KEY", settings.PUBNUB_PUBLISH_KEY)
    os.environ.setdefault("PUBNUB_SUBSCRIBE_KEY", settings.PUBNUB_SUBSCRIBE_KEY)
    os.environ.setdefault("PUBNUB_SECRET_KEY", settings.PUBNUB_SECRET_KEY)
    os.environ.setdefault("USER_ID", "poly_synergy_flow")

    code = version.executable
    namespace = {}

    try:
        exec(code, namespace)
    except Exception:
        return JSONResponse({
            "error": "Failed to execute code",
            "details": traceback.format_exc()
        }, status_code=400)

    fn = namespace.get("execute_with_mock_start_node")
    if not callable(fn):
        return JSONResponse({"error": "Function 'execute_with_mock_start_node' not found"}, status_code=400)

    try:
        run_id = str(uuid.uuid4())
        if active_listener_service.has_listener(str(version.id)):
            send_flow_event(str(version.id), run_id, None, "run_start")

        if inspect.iscoroutinefunction(fn):
            result = await fn(mock_node_id, run_id, sub_stage)
        else:
            result = fn(mock_node_id, run_id, sub_stage)

        if active_listener_service.has_listener(str(version.id)):
            send_flow_event(str(version.id), run_id, None, "run_end")

        return {"status": "mock executed", "result": result}
    except Exception:
        return JSONResponse({
            "error": "Function execution failed",
            "details": traceback.format_exc()
        }, status_code=500)