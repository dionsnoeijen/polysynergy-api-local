"""Possession chat WebSocket endpoint.

Separate from execution.py (which streams flow runtime events) and
public_chat.py (embeddable chat widgets). This endpoint is the
platform-control chat: users talk to orchestrator itself, the agent
drives the portal UI via possession.
"""

import json
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from db.session import get_db
from possession import MessageRouter, WebSocketSession
from possession_chat.agent import create_session_components
from utils.websocket_auth import validate_websocket_token

router = APIRouter()


@router.websocket("/chat")
async def possession_chat_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    # Authenticate BEFORE accepting the connection.
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    db = next(get_db())
    try:
        account = await validate_websocket_token(token, db)
    except Exception as e:
        await websocket.close(code=1008, reason=str(e))
        return
    finally:
        db.close()

    # Build the session and hand off to possession's WebSocketSession.
    bus, runner = create_session_components(account)
    router_ = MessageRouter()
    session = WebSocketSession(
        agent_runner=runner,
        event_bus=bus,
        router=router_,
        session_id=f"account:{account.id}",
    )

    try:
        await session.handle(websocket)
    except WebSocketDisconnect:
        pass
