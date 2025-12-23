"""
Embedded chat API endpoints - Public access with embed token authentication.

These endpoints allow external SPAs to interact with chat windows
using embed token authentication instead of Cognito.
"""
import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from models import NodeSetup, NodeSetupVersion
from repositories.node_setup_repository import NodeSetupRepository, get_node_setup_repository
from schemas.embed_token import (
    EmbeddedChatConfigOut,
    EmbeddedExecuteIn,
    EmbeddedResumeIn,
    EmbeddedPromptsOut,
    EmbeddedPromptOut,
)
from services.active_listeners_service import get_active_listeners_service
from services.lambda_service import get_lambda_service, LambdaService
from services.mock_sync_service import MockSyncService, get_mock_sync_service
from utils.embed_token_auth import EmbedTokenContext, get_embed_token_context
from core.settings import settings
from core.logging_config import get_logger
from polysynergy_node_runner.services.active_listeners_service import ActiveListenersService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/config/", response_model=EmbeddedChatConfigOut)
async def get_embedded_config(
    context: EmbedTokenContext = Depends(get_embed_token_context),
):
    """
    Get chat configuration for embedded widget.

    **Authentication:** Requires valid embed token in `X-Embed-Token` header.

    Returns configuration needed to initialize the embedded chat widget.
    """
    return EmbeddedChatConfigOut(
        chat_window_id=context.chat_window.id,
        chat_window_name=context.chat_window.name,
        sessions_enabled=context.sessions_enabled,
        sidebar_visible=context.sidebar_visible,
    )


@router.get("/prompts/", response_model=EmbeddedPromptsOut)
async def get_embedded_prompts(
    context: EmbedTokenContext = Depends(get_embed_token_context),
    db: Session = Depends(get_db),
):
    """
    Get available prompt nodes for this chat window.

    **Authentication:** Requires valid embed token in `X-Embed-Token` header.

    Returns list of prompt nodes that can be targeted for message injection.
    Used to display tabs when multiple prompts are available.
    """
    # Get node setup for chat window
    node_setup = db.query(NodeSetup).filter(
        NodeSetup.content_type == "chat_window",
        NodeSetup.object_id == context.chat_window.id
    ).first()

    if not node_setup:
        return EmbeddedPromptsOut(prompts=[])

    # Get the latest version
    version = db.query(NodeSetupVersion).filter(
        NodeSetupVersion.node_setup_id == node_setup.id
    ).order_by(NodeSetupVersion.created_at.desc()).first()

    if not version:
        return EmbeddedPromptsOut(prompts=[])

    content = version.content or {}
    nodes = content.get("nodes", [])

    # Find all Prompt nodes
    prompt_nodes = []
    for node in nodes:
        node_path = node.get("path", "")
        if node_path == "polysynergy_nodes.play.prompt.Prompt":
            # Get the name from variables
            name = node.get("handle", "Prompt")
            for var in node.get("variables", []):
                if var.get("handle") == "name" and var.get("value"):
                    name = var["value"]
                    break

            prompt_nodes.append(EmbeddedPromptOut(
                id=uuid.UUID(node["id"]),
                name=name,
                handle=node.get("handle", "")
            ))

    return EmbeddedPromptsOut(prompts=prompt_nodes)


@router.post("/execute/")
async def execute_embedded_chat(
    data: EmbeddedExecuteIn,
    context: EmbedTokenContext = Depends(get_embed_token_context),
    db: Session = Depends(get_db),
    active_listener_service: ActiveListenersService = Depends(get_active_listeners_service),
    lambda_service: LambdaService = Depends(get_lambda_service),
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
    mock_sync_service: MockSyncService = Depends(get_mock_sync_service),
):
    """
    Execute chat with a message.

    **Authentication:** Requires valid embed token in `X-Embed-Token` header.

    Triggers the chat window's node setup execution with the provided message.
    The response will be streamed via WebSocket connection.
    """
    # Get node setup for chat window
    node_setup = db.query(NodeSetup).filter(
        NodeSetup.content_type == "chat_window",
        NodeSetup.object_id == context.chat_window.id
    ).first()

    if not node_setup:
        raise HTTPException(status_code=404, detail="Chat window configuration not found")

    # Get the latest version
    version = db.query(NodeSetupVersion).filter(
        NodeSetupVersion.node_setup_id == node_setup.id
    ).order_by(NodeSetupVersion.created_at.desc()).first()

    if not version:
        raise HTTPException(status_code=404, detail="Chat window has no versions")

    # Find the prompt node to pass the message to
    # We need to find the node that receives the user input
    content = version.content or {}
    nodes = content.get("nodes", [])

    # Find entry point - typically a PlayConfig or Prompt node
    entry_node_id = None
    for node in nodes:
        if node.get("has_play_button"):
            entry_node_id = node.get("id")
            break

    if not entry_node_id:
        raise HTTPException(status_code=400, detail="Chat window has no entry point configured")

    # Set up active listener for WebSocket communication
    active_listener_service.set_listener(str(version.id))

    logger.info_ctx("Embedded chat execution starting",
        version_id=str(version.id),
        chat_window_id=str(context.chat_window.id),
        project_id=str(context.project.id),
        message_length=len(data.message)
    )

    print(f"[EMBEDDED] EXECUTE_NODE_SETUP_LOCAL = {settings.EXECUTE_NODE_SETUP_LOCAL}")
    if settings.EXECUTE_NODE_SETUP_LOCAL:
        # Local execution
        from api.v1.execution.mock import execute_local
        print(f"[EMBEDDED] Starting local execution for version {version.id}, entry_node {entry_node_id}")
        print(f"[EMBEDDED] Message: {data.message[:100] if data.message else 'None'}...")
        try:
            result = await execute_local(
                context.project,
                version,
                uuid.UUID(entry_node_id),
                "mock",
                active_listener_service,
                input_data={
                    "message": data.message,
                    "session_id": str(data.session_id) if data.session_id else None,
                    "prompt_node_id": str(data.prompt_node_id) if data.prompt_node_id else None
                }
            )
            print(f"[EMBEDDED] Execution completed successfully, result type: {type(result)}")
            # Return a simple dict instead of passing through JSONResponse
            # The JSONResponse from execute_local may have issues with streaming
            return {"status": "executed", "message": "Chat execution completed"}
        except Exception as e:
            print(f"[EMBEDDED] Execution failed: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

    # Lambda execution
    function_name = f"node_setup_{version.id}_mock"
    mock_sync_service.sync_if_needed(version, context.project)

    payload = {
        "node_id": entry_node_id,
        "s3_key": f"{context.project.tenant_id}/{context.project.id}/{function_name}.py",
        "mock": True,
        "sub_stage": "mock",
        "input_data": {
            "message": data.message,
            "session_id": str(data.session_id) if data.session_id else None,
            "prompt_node_id": str(data.prompt_node_id) if data.prompt_node_id else None
        }
    }

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda_service.invoke_lambda, function_name, payload)
        return response
    except Exception as e:
        logger.error_ctx("Embedded chat execution failed",
            error=str(e),
            version_id=str(version.id)
        )
        raise HTTPException(status_code=500, detail="Chat execution failed")


@router.post("/resume/")
async def resume_embedded_chat(
    data: EmbeddedResumeIn,
    context: EmbedTokenContext = Depends(get_embed_token_context),
):
    """
    Resume a paused chat execution (HITL - Human In The Loop).

    **Authentication:** Requires valid embed token in `X-Embed-Token` header.

    Continues a chat execution that was paused waiting for user input.
    """
    # TODO: Implement HITL resume logic
    # This will need to signal the paused execution to continue
    return {"status": "resumed", "execution_id": str(data.execution_id)}


@router.get("/version-id/")
async def get_chat_version_id(
    context: EmbedTokenContext = Depends(get_embed_token_context),
    db: Session = Depends(get_db),
):
    """
    Get the version ID for WebSocket connection.

    **Authentication:** Requires valid embed token in `X-Embed-Token` header.

    Returns the version ID needed to establish WebSocket connection.
    """
    node_setup = db.query(NodeSetup).filter(
        NodeSetup.content_type == "chat_window",
        NodeSetup.object_id == context.chat_window.id
    ).first()

    if not node_setup:
        raise HTTPException(status_code=404, detail="Chat window configuration not found")

    version = db.query(NodeSetupVersion).filter(
        NodeSetupVersion.node_setup_id == node_setup.id
    ).order_by(NodeSetupVersion.created_at.desc()).first()

    if not version:
        raise HTTPException(status_code=404, detail="Chat window has no versions")

    return {"version_id": str(version.id)}
