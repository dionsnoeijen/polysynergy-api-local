import asyncio
import inspect
import os
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from models import Project, NodeSetupVersion
from repositories.node_setup_repository import get_node_setup_repository, NodeSetupRepository
from services.lambda_service import get_lambda_service, LambdaService
from services.local_log_service import LogCapture
from services.active_listeners_service import get_active_listeners_service
from polysynergy_node_runner.services.active_listeners_service import ActiveListenersService
from db.session import get_db
from core.settings import settings
from core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ResumeRequest(BaseModel):
    run_id: str
    resume_node_id: str
    user_input: dict


@router.post("/{version_id}/resume/", response_model=None)
async def resume_flow(
    version_id: uuid.UUID,
    resume_request: ResumeRequest,
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
    active_listener_service: ActiveListenersService = Depends(get_active_listeners_service)
):
    """
    Resume a paused Human-in-the-Loop flow execution.

    This endpoint is called when a user responds to a HIL confirmation request.
    It updates the HIL node with the user's response and resumes execution from that node.

    Args:
        version_id: The node setup version ID
        resume_request: Contains run_id, resume_node_id, and user_input

    Returns:
        JSONResponse with execution result
    """
    # Set up the listener for WebSocket events
    active_listener_service.set_listener(str(version_id))

    version = node_setup_repository.get_or_404(version_id)

    # Get project via version.node_setup relationship
    parent = version.node_setup.resolve_parent(db)
    project = parent.project if hasattr(parent, 'project') else None

    logger.info_ctx("HIL Resume execution starting",
        version_id=str(version_id),
        run_id=resume_request.run_id,
        resume_node_id=resume_request.resume_node_id,
        project_id=str(project.id) if project else "unknown",
        execution_mode="local" if settings.EXECUTE_NODE_SETUP_LOCAL else "lambda"
    )

    if settings.EXECUTE_NODE_SETUP_LOCAL:
        logger.debug("Executing resume locally")
        return await execute_resume_local(
            version,
            resume_request.run_id,
            resume_request.resume_node_id,
            resume_request.user_input,
            project
        )

    # Lambda execution
    function_name = f"node_setup_{version_id}_mock"

    # Build s3_key with project info if available
    s3_key = f"{function_name}.py"
    if project:
        s3_key = f"{project.tenant_id}/{project.id}/{function_name}.py"

    payload = {
        "resume": True,
        "run_id": resume_request.run_id,
        "resume_node_id": resume_request.resume_node_id,
        "user_input": resume_request.user_input,
        "s3_key": s3_key
    }

    logger.info_ctx("Invoking Lambda for HIL resume",
        function_name=function_name,
        run_id=resume_request.run_id
    )

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda_service.invoke_lambda, function_name, payload)
        logger.info_ctx("Lambda resume execution successful",
            version_id=str(version_id),
            run_id=resume_request.run_id
        )
        return {"status": "resumed", "result": response}
    except Exception as e:
        msg = str(e)
        logger.error_ctx("Lambda resume execution failed",
            version_id=str(version_id),
            run_id=resume_request.run_id,
            error_type=type(e).__name__,
            error_message=msg
        )
        raise HTTPException(status_code=500, detail={"error": "Lambda resume error", "details": msg})


async def execute_resume_local(
    version: NodeSetupVersion,
    run_id: str,
    resume_node_id: str,
    user_input: dict,
    project: Project | None = None
) -> JSONResponse:
    """Execute resume locally (for development/testing)"""
    # Set environment variables if project is available
    if project:
        os.environ['PROJECT_ID'] = str(project.id)
        os.environ['TENANT_ID'] = str(project.tenant_id)

    os.environ.setdefault("AWS_REGION", settings.AWS_REGION)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)

    code = version.executable
    namespace = {}

    # Use LogCapture to capture all stdout/stderr during local execution
    with LogCapture(str(version.id), "resume") as log_capture:
        log_capture.add_custom_log(f"RESUME START RequestId: {run_id} Version: {version.id}")

        try:
            log_capture.add_custom_log("Loading and executing node setup code for resume...")
            exec(code, namespace)
        except Exception:
            error_details = traceback.format_exc()
            log_capture.add_custom_log(f"[ERROR] Failed to execute code: {error_details}")
            return JSONResponse({
                "error": "Failed to execute code",
                "details": error_details
            }, status_code=400)

        fn = namespace.get("execute_with_resume")
        if not callable(fn):
            error_msg = "Function 'execute_with_resume' not found in executable"
            log_capture.add_custom_log(f"[ERROR] {error_msg}")
            return JSONResponse({"error": error_msg}, status_code=400)

        try:
            log_capture.add_custom_log(
                f"Starting resume execution with run_id: {run_id}, "
                f"resume_node_id: {resume_node_id}, user_input: {user_input}"
            )

            # Execute the resume function
            if inspect.iscoroutinefunction(fn):
                log_capture.add_custom_log("Executing async resume function...")
                result = await fn(run_id, resume_node_id, user_input)
            else:
                log_capture.add_custom_log("Executing sync resume function...")
                result = fn(run_id, resume_node_id, user_input)

            log_capture.add_custom_log(
                f"Resume execution completed successfully. "
                f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict result'}"
            )

            log_capture.add_custom_log(f"RESUME END RequestId: {run_id}")
            return JSONResponse({"status": "resumed", "result": result})

        except Exception:
            error_details = traceback.format_exc()
            log_capture.add_custom_log(f"[ERROR] Resume execution failed: {error_details}")
            return JSONResponse({
                "error": "Resume execution failed",
                "details": error_details
            }, status_code=500)
