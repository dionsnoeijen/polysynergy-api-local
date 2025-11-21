"""
Public chat WebSocket endpoint for external applications and demos.
This endpoint allows unauthenticated access to chat streams for specific chat windows.
"""
import asyncio
import os
from typing import Optional
from uuid import UUID

from fastapi import WebSocket, APIRouter, WebSocketDisconnect, Query
import redis.asyncio as redis
from sqlalchemy.orm import Session

from db.session import get_db
from models import ChatWindow, NodeSetup

router = APIRouter()
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
redis_client = redis.from_url(
    redis_url,
    decode_responses=True,
    db=0
)


async def get_flow_id_from_chat_window(chat_window_id: UUID, db: Session) -> Optional[str]:
    """
    Get the flow_id (NodeSetup ID) for a given chat window.

    Args:
        chat_window_id: Chat window UUID
        db: Database session

    Returns:
        flow_id (NodeSetup ID) as string, or None if not found
    """
    # Find the NodeSetup associated with this chat window
    node_setup = db.query(NodeSetup).filter_by(
        content_type="chat_window",
        object_id=chat_window_id
    ).first()

    if not node_setup:
        return None

    return str(node_setup.id)


@router.websocket("/public/chat/{chat_window_id}")
async def public_chat_ws(
    websocket: WebSocket,
    chat_window_id: UUID,
    api_key: Optional[str] = Query(None, description="API key for future authentication")
):
    """
    Public WebSocket endpoint for chat streams.

    Currently open for demo purposes. Will require API key authentication in the future.
    Only streams chat messages, no execution details or interaction events.

    Args:
        websocket: WebSocket connection
        chat_window_id: UUID of the chat window to stream
        api_key: Optional API key (placeholder for future auth)
    """
    # Get database session
    db = next(get_db())

    try:
        # Verify chat window exists and get flow_id
        chat_window = db.query(ChatWindow).filter_by(id=chat_window_id).first()

        if not chat_window:
            await websocket.close(code=1008, reason="Chat window not found")
            print(f'❌ Chat window not found: {chat_window_id}')
            return

        flow_id = await get_flow_id_from_chat_window(chat_window_id, db)

        if not flow_id:
            await websocket.close(code=1008, reason="No published flow found for this chat window")
            print(f'❌ No flow found for chat window: {chat_window_id}')
            return

        # TODO: Future API key validation
        # if api_key:
        #     validate_api_key(api_key, chat_window)

        print(f'✅ Public chat WebSocket connection for chat_window={chat_window_id}, flow_id={flow_id}')

    except Exception as e:
        print(f'❌ Error setting up public chat WebSocket: {e}')
        await websocket.close(code=1011, reason="Internal server error")
        return
    finally:
        db.close()

    # Accept the connection
    await websocket.accept()
    print(f'ACCEPTED PUBLIC CHAT CONNECTION for chat_window={chat_window_id}')

    # Subscribe only to chat stream channel (no execution or interaction events)
    chat_channel = f"chat_stream:{flow_id}"

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(chat_channel)

    async def forward_messages():
        try:
            async for message in pubsub.listen():
                # Skip subscription confirmation messages
                if message["type"] == "subscribe":
                    print(f"✅ Subscribed to channel: {message['channel']}")
                    continue
                # Only forward actual messages
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except asyncio.CancelledError:
            print(f"🛑 Forward task cancelled for chat_window={chat_window_id}")
            await pubsub.unsubscribe(chat_channel)
            await pubsub.close()
            raise

    task = asyncio.create_task(forward_messages())
    try:
        while True:
            try:
                # Wait for client messages or task completion
                message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                # Handle ping/pong for connection health
                if message == "ping":
                    await websocket.send_text("pong")
                    print(f"💓 Responded to ping for chat_window={chat_window_id}")
            except asyncio.TimeoutError:
                # Check if the task is still running
                if task.done():
                    break
                continue
            except WebSocketDisconnect:
                print(f"🔌 WebSocket disconnected: chat_window={chat_window_id}")
                break
    except Exception as e:
        print(f"❌ WebSocket error for chat_window={chat_window_id}: {e}")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
