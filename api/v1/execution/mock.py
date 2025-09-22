import asyncio
import inspect
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
from services.local_log_service import LogCapture
from utils.get_current_account import get_project_or_403
from core.settings import settings
from core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

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
    # Log execution context
    logger.info_ctx("Mock execution starting",
        version_id=str(version_id),
        node_id=str(mock_node_id),
        project_id=str(project.id),
        sub_stage=sub_stage,
        execution_mode="local" if settings.EXECUTE_NODE_SETUP_LOCAL else "lambda"
    )

    active_listener_service.set_listener(str(version_id))
    version = node_setup_repository.get_or_404(version_id)

    if settings.EXECUTE_NODE_SETUP_LOCAL:
        logger.debug("Executing locally")
        return await execute_local(project, version, mock_node_id, sub_stage, active_listener_service)

    function_name = f"node_setup_{version_id}_mock"
    mock_sync_service.sync_if_needed(version, project)
    payload = {
        "node_id": str(mock_node_id),
        "s3_key": f"{project.tenant_id}/{project.id}/{function_name}.py",
        "mock": True,
        "sub_stage": sub_stage,
    }

    logger.info_ctx("Invoking Lambda function",
        function_name=function_name,
        payload_size=len(str(payload))
    )

    delay = INITIAL_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda_service.invoke_lambda, function_name, payload)
            logger.info_ctx("Lambda execution successful",
                version_id=str(version_id),
                attempts=attempt
            )
            return {"status": "mock executed", "result": response}
        except Exception as e:
            msg = str(e)
            if "ResourceConflictException" in msg and "Pending" in msg:
                logger.warning_ctx(f"Lambda pending, retry {attempt}/{MAX_RETRIES} in {delay}s",
                    version_id=str(version_id),
                    retry_attempt=attempt,
                    delay_seconds=delay
                )
                time.sleep(delay)
                delay *= 2
            else:
                logger.error_ctx("Lambda execution failed",
                    version_id=str(version_id),
                    error_type=type(e).__name__,
                    error_message=msg,
                    attempts=attempt
                )
                raise HTTPException(status_code=500, detail={"error": "Lambda error", "details": msg})

    logger.error_ctx("Lambda stuck in pending status after max retries",
        version_id=str(version_id),
        max_retries=MAX_RETRIES
    )
    raise HTTPException(status_code=503, detail="Lambda remained in pending status")


async def execute_local(
    project: Project,
    version: NodeSetupVersion,
    mock_node_id: uuid.UUID,
    sub_stage: str,
    active_listener_service: ActiveListenersService
) -> JSONResponse:
    os.environ['PROJECT_ID'] = str(project.id)
    os.environ['TENANT_ID'] = str(project.tenant_id)
    os.environ.setdefault("AWS_REGION", settings.AWS_REGION)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)

    code = version.executable
    namespace = {}
    
    # Use LogCapture to capture all stdout/stderr during local execution
    with LogCapture(str(version.id), "mock") as log_capture:
        log_capture.add_custom_log(f"START RequestId: local-{uuid.uuid4()} Version: {version.id}")
        
        try:
            log_capture.add_custom_log("Loading and executing node setup code...")
            exec(code, namespace)
        except Exception:
            error_details = traceback.format_exc()
            log_capture.add_custom_log(f"[ERROR] Failed to execute code: {error_details}")
            return JSONResponse({
                "error": "Failed to execute code",
                "details": error_details
            }, status_code=400)

        fn = namespace.get("execute_with_mock_start_node")
        if not callable(fn):
            error_msg = "Function 'execute_with_mock_start_node' not found"
            log_capture.add_custom_log(f"[ERROR] {error_msg}")
            return JSONResponse({"error": error_msg}, status_code=400)

        try:
            run_id = str(uuid.uuid4())
            log_capture.add_custom_log(f"Starting execution with run_id: {run_id}, mock_node_id: {mock_node_id}, sub_stage: {sub_stage}")
            
            if active_listener_service.has_listener(str(version.id), first_run=True):
                send_flow_event(str(version.id), run_id, None, "run_start")
                log_capture.add_custom_log("Sent run_start event via WebSocket")
            
            # Execute the function and capture all output
            if inspect.iscoroutinefunction(fn):
                log_capture.add_custom_log("Executing async function...")
                result = await fn(mock_node_id, run_id, sub_stage)
            else:
                log_capture.add_custom_log("Executing sync function...")
                result = fn(mock_node_id, run_id, sub_stage)
                
            log_capture.add_custom_log(f"Function execution completed successfully. Result keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict result'}")
            
            if active_listener_service.has_listener(str(version.id)):
                send_flow_event(str(version.id), run_id, None, "run_end")
                log_capture.add_custom_log("Sent run_end event via WebSocket")

            log_capture.add_custom_log(f"END RequestId: local-{run_id}")
            return JSONResponse({"status": "mock executed", "result": result})
            
        except Exception:
            error_details = traceback.format_exc()
            log_capture.add_custom_log(f"[ERROR] Function execution failed: {error_details}")
            return JSONResponse({
                "error": "Function execution failed", 
                "details": error_details
            }, status_code=500)


@router.post("/{version_id}/start/", response_model=None)
async def start_execution(
    version_id: uuid.UUID,
    request_data: dict,
    project: Project = Depends(get_project_or_403),
    active_listener_service: ActiveListenersService = Depends(get_active_listeners_service),
    lambda_service: LambdaService = Depends(get_lambda_service),
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
    mock_sync_service: MockSyncService = Depends(get_mock_sync_service)
):
    """
    Fire-and-forget execution endpoint.
    Starts execution immediately and returns run_id without waiting for completion.
    Real-time updates come via WebSocket.
    """
    # Extract parameters from request body
    mock_node_id = uuid.UUID(request_data.get("node_id"))
    sub_stage = request_data.get("sub_stage", "mock")
    # Note: project_id is handled by get_project_or_403 dependency from query params
    
    # Set up the listener
    active_listener_service.set_listener(str(version_id))
    version = node_setup_repository.get_or_404(version_id)
    
    # Generate run_id immediately
    run_id = str(uuid.uuid4())
    
    # Start execution in background - don't await!
    if settings.EXECUTE_NODE_SETUP_LOCAL:
        # Schedule the execution as a background task
        asyncio.create_task(
            execute_local_background(
                project, version, mock_node_id, sub_stage, 
                active_listener_service, run_id
            )
        )
    else:
        # Schedule Lambda execution as background task
        asyncio.create_task(
            execute_lambda_background(
                project, version, mock_node_id, sub_stage,
                active_listener_service, lambda_service, mock_sync_service, run_id
            )
        )
    
    # Return immediately with run_id
    return JSONResponse({
        "run_id": run_id,
        "status": "started",
        "started_at": time.time()
    })


async def execute_local_background(
    project: Project,
    version: NodeSetupVersion,
    mock_node_id: uuid.UUID,
    sub_stage: str,
    active_listener_service: ActiveListenersService,
    run_id: str
):
    """Background execution that doesn't block the API response"""
    try:
        # Same setup as execute_local but runs in background
        os.environ['PROJECT_ID'] = str(project.id)
        os.environ['TENANT_ID'] = str(project.tenant_id)
        os.environ.setdefault("AWS_REGION", settings.AWS_REGION)
        os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)

        code = version.executable
        namespace = {}
        
        with LogCapture(str(version.id), "mock") as log_capture:
            log_capture.add_custom_log(f"BACKGROUND START RequestId: {run_id} Version: {version.id}")
            
            try:
                log_capture.add_custom_log("Loading and executing node setup code (background)...")
                exec(code, namespace)
            except Exception:
                error_details = traceback.format_exc()
                log_capture.add_custom_log(f"[ERROR] Failed to execute code: {error_details}")
                return

            fn = namespace.get("execute_with_mock_start_node")
            if not callable(fn):
                error_msg = "Function 'execute_with_mock_start_node' not found"
                log_capture.add_custom_log(f"[ERROR] {error_msg}")
                return

            try:
                log_capture.add_custom_log(f"Starting background execution with run_id: {run_id}, mock_node_id: {mock_node_id}, sub_stage: {sub_stage}")
                
                if active_listener_service.has_listener(str(version.id), first_run=True):
                    send_flow_event(str(version.id), run_id, None, "run_start")
                    log_capture.add_custom_log("Sent run_start event via WebSocket")
                
                # Execute the function - this can take a long time but doesn't block API
                if inspect.iscoroutinefunction(fn):
                    log_capture.add_custom_log("Executing async function (background)...")
                    result = await fn(mock_node_id, run_id, sub_stage)
                else:
                    log_capture.add_custom_log("Executing sync function (background)...")
                    result = fn(mock_node_id, run_id, sub_stage)
                    
                log_capture.add_custom_log(f"Background execution completed successfully. Result keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict result'}")
                
                if active_listener_service.has_listener(str(version.id)):
                    send_flow_event(str(version.id), run_id, None, "run_end")
                    log_capture.add_custom_log("Sent run_end event via WebSocket")

                log_capture.add_custom_log(f"BACKGROUND END RequestId: {run_id}")
                
            except Exception:
                error_details = traceback.format_exc()
                log_capture.add_custom_log(f"[ERROR] Background execution failed: {error_details}")
                
    except Exception as e:
        logger.error(f"Background execution error: {str(e)}")


async def execute_lambda_background(
    project: Project,
    version: NodeSetupVersion,
    mock_node_id: uuid.UUID,
    sub_stage: str,
    active_listener_service: ActiveListenersService,
    lambda_service: LambdaService,
    mock_sync_service: MockSyncService,
    run_id: str
):
    """Background Lambda execution"""
    try:
        function_name = f"node_setup_{version.id}_mock"
        mock_sync_service.sync_if_needed(version, project)
        payload = {
            "node_id": str(mock_node_id),
            "s3_key": f"{project.tenant_id}/{project.id}/{function_name}.py",
            "mock": True,
            "sub_stage": sub_stage,
            "run_id": run_id  # Pass run_id to Lambda
        }
        
        # Note: Lambda will send run_start and run_end events itself
        # No need to send from API to avoid duplicates
        
        delay = INITIAL_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda_service.invoke_lambda, function_name, payload)
                logger.info(f"Background Lambda execution completed for run_id: {run_id}")
                return response
            except Exception as e:
                msg = str(e)
                if "ResourceConflictException" in msg and "Pending" in msg:
                    logger.warning(f"Lambda pending, retry {attempt}/{MAX_RETRIES} in {delay}s")
                    await asyncio.sleep(delay)  # Use async sleep in background
                    delay *= 2
                else:
                    logger.error(f"Background Lambda exec error: {msg}")
                    return
        
        logger.error(f"Background Lambda remained in pending status for run_id: {run_id}")
        
    except Exception as e:
        logger.error(f"Background Lambda execution error: {str(e)}")