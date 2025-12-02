"""
Route execution endpoint for self-hosted mode.
Handles execution requests from the router service.
"""
import uuid
import os
import json
import inspect
import traceback
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Project, NodeSetupVersion
from db.session import get_db
from repositories.node_setup_repository import get_node_setup_repository, NodeSetupRepository
from services.active_listeners_service import get_active_listeners_service
from polysynergy_node_runner.services.active_listeners_service import ActiveListenersService
from polysynergy_node_runner.execution_context.send_flow_event import send_flow_event
from services.local_log_service import LogCapture
from core.settings import settings
from core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


class RouteExecutionRequest(BaseModel):
    """Request payload from router for route execution."""
    node_setup_version_id: str
    tenant_id: str
    project_id: str
    stage: str
    variables: Dict[str, Any]
    method: str
    path: str
    query_params: Dict[str, Any] | None = None
    headers: Dict[str, str] | None = None
    body: Any | None = None


@router.post("/")
async def execute_route(
    request: RouteExecutionRequest,
    db: Session = Depends(get_db),
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
    active_listener_service: ActiveListenersService = Depends(get_active_listeners_service)
):
    """
    Execute a route locally (self-hosted mode).
    Called by the router service when a route is matched.
    """
    logger.info_ctx("Route execution starting",
        version_id=request.node_setup_version_id,
        path=request.path,
        method=request.method,
        variables=request.variables,
        stage=request.stage
    )

    try:
        # Fetch NodeSetupVersion
        version_uuid = uuid.UUID(request.node_setup_version_id)
        version = node_setup_repository.get_or_404(version_uuid)

        # Fetch Project
        project_uuid = uuid.UUID(request.project_id)
        tenant_uuid = uuid.UUID(request.tenant_id)
        project = db.query(Project).filter(
            Project.id == project_uuid,
            Project.tenant_id == tenant_uuid
        ).first()

        if not project:
            logger.error_ctx("Project not found",
                project_id=request.project_id,
                tenant_id=request.tenant_id
            )
            raise HTTPException(status_code=404, detail="Project not found")

        # Execute the route
        return await execute_route_local(request, version, project, active_listener_service)

    except ValueError as e:
        logger.error_ctx("Invalid UUID",
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=f"Invalid ID: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error_ctx("Route execution failed",
            version_id=request.node_setup_version_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


async def execute_route_local(
    request: RouteExecutionRequest,
    version: NodeSetupVersion,
    project: Project,
    active_listener_service: ActiveListenersService
) -> Response:
    """Execute a route in local/self-hosted mode."""

    # Set environment variables (same as mock execution)
    os.environ['PROJECT_ID'] = str(project.id)
    os.environ['TENANT_ID'] = str(project.tenant_id)
    os.environ.setdefault("AWS_REGION", settings.AWS_REGION)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)

    database_url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    os.environ.setdefault("DATABASE_URL", database_url)
    os.environ.setdefault("SECTIONS_DATABASE_URL", settings.SECTIONS_DATABASE_URL)

    # Load executable code
    code = version.executable
    namespace = {}

    with LogCapture(str(version.id), request.stage) as log_capture:
        log_capture.add_custom_log(f"START RequestId: local-{uuid.uuid4()} Version: {version.id}")

        try:
            log_capture.add_custom_log("Loading node setup code for route execution...")
            exec(code, namespace)
        except Exception:
            error_details = traceback.format_exc()
            log_capture.add_custom_log(f"[ERROR] Failed to execute code: {error_details}")
            return Response(
                content=json.dumps({"error": "Failed to execute code", "details": error_details}),
                status_code=500,
                media_type="application/json"
            )

        # Get the production execution function
        fn = namespace.get("execute_with_production_start")
        if not callable(fn):
            error_msg = "Function 'execute_with_production_start' not found"
            log_capture.add_custom_log(f"[ERROR] {error_msg}")
            return Response(
                content=json.dumps({"error": error_msg}),
                status_code=500,
                media_type="application/json"
            )

        try:
            run_id = str(uuid.uuid4())
            log_capture.add_custom_log(f"Starting route execution: run_id={run_id}, method={request.method}, path={request.path}")

            # Transform router payload to Lambda event format
            event = {
                "httpMethod": request.method,
                "headers": request.headers or {},
                "body": request.body or "",
                "queryStringParameters": request.query_params or {},
                "pathParameters": request.variables,  # Path variables from route matching
                "cookies": {}  # Could extract from headers if needed
            }

            # Check for active listeners and send events (for test/mock stages)
            is_test_run = request.stage in ["mock", "test"]
            if is_test_run and active_listener_service.has_listener(str(version.id), required_stage=request.stage, first_run=True):
                send_flow_event(str(version.id), run_id, None, "run_start")

            # Execute the function
            if inspect.iscoroutinefunction(fn):
                execution_flow, flow, state, is_schedule = await fn(event, run_id, request.stage)
            else:
                execution_flow, flow, state, is_schedule = fn(event, run_id, request.stage)

            # Send end event
            if is_test_run and active_listener_service.has_listener(str(version.id), required_stage=request.stage):
                send_flow_event(str(version.id), run_id, None, "run_end")

            # Find HttpResponse node and extract response
            last_http_response = next(
                (node for node in reversed(execution_flow.get("nodes_order", []))
                 if node.get("type", "").startswith("HttpResponse")),
                None
            )

            if last_http_response:
                http_response_node = state.get_node_by_id(last_http_response.get("id", ""))
                node_response = http_response_node.response

                if isinstance(node_response, dict):
                    status_code = node_response.get('status', node_response.get('statusCode', 200))
                    headers = node_response.get('headers', {})
                    body = node_response.get('body', '')
                else:
                    status_code = 200
                    headers = {"Content-Type": "application/json"}
                    body = str(node_response) if node_response is not None else ""

                log_capture.add_custom_log(f"END RequestId: local-{run_id}, status={status_code}")

                return Response(
                    content=body,
                    status_code=status_code,
                    headers=headers,
                    media_type=headers.get("Content-Type", "text/plain")
                )

            # No HttpResponse node found
            if is_schedule:
                log_capture.add_custom_log("Schedule execution completed (no HttpResponse needed)")
                return Response(
                    content=json.dumps({"message": "Schedule executed successfully"}),
                    status_code=200,
                    media_type="application/json"
                )
            else:
                log_capture.add_custom_log("[ERROR] No HttpResponse node found in route flow")
                return Response(
                    content=json.dumps({"error": "No valid HttpResponse node found"}),
                    status_code=500,
                    media_type="application/json"
                )

        except Exception:
            error_details = traceback.format_exc()
            log_capture.add_custom_log(f"[ERROR] Function execution failed: {error_details}")
            return Response(
                content=json.dumps({"error": "Function execution failed", "details": error_details}),
                status_code=500,
                media_type="application/json"
            )
