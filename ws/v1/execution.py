import asyncio
import os
from typing import Optional

from fastapi import WebSocket, APIRouter, WebSocketDisconnect, Query
import redis.asyncio as redis

from db.session import get_db
from utils.websocket_auth import validate_websocket_token, validate_websocket_embed_token

router = APIRouter()
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
redis_client = redis.from_url(
    redis_url,
    decode_responses=True,
    db=0
)

@router.websocket("/execution/{flow_id}")
async def execution_ws(
    websocket: WebSocket,
    flow_id: str,
    token: Optional[str] = Query(None),
    embed_token: Optional[str] = Query(None)
):
    print(f'🔌 WebSocket connection attempt for flow_id={flow_id}')
    print(f'🔌 Token provided: {bool(token)}, Embed token provided: {bool(embed_token)}')
    if embed_token:
        print(f'🔌 Embed token value: {embed_token[:20]}...')

    # Validate authentication before accepting connection
    # Support both JWT token (Cognito) and embed token (public embedding)
    db = next(get_db())
    try:
        if embed_token:
            # Embed token authentication for public chat widgets
            print(f'🔌 Validating embed token...')
            auth_context = await validate_websocket_embed_token(embed_token, db)
            print(f'✅ Authenticated WebSocket connection via embed token for chat window: {auth_context.chat_window_id}')
        elif token:
            # JWT token authentication for authenticated users
            account = await validate_websocket_token(token, db)
            print(f'✅ Authenticated WebSocket connection for account: {account.email}')
        else:
            print(f'❌ WebSocket authentication failed: No token provided')
            await websocket.close(code=1008, reason="Missing authentication token")
            return
    except Exception as e:
        print(f'❌ WebSocket authentication failed: {e}')
        import traceback
        traceback.print_exc()
        await websocket.close(code=1008, reason=str(e))
        return
    finally:
        db.close()

    await websocket.accept()
    print(f'ACCEPTED CONNECTION for flow_id={flow_id}')

    exec_channel = f"execution_updates:{flow_id}"
    chat_channel = f"chat_stream:{flow_id}"
    interaction_channel = f"interaction_events:{flow_id}"

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(exec_channel, chat_channel, interaction_channel)

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
            print(f"🛑 Forward task cancelled for flow_id={flow_id}")
            await pubsub.unsubscribe(exec_channel, chat_channel, interaction_channel)
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
                    print(f"💓 Responded to ping for flow_id={flow_id}")
            except asyncio.TimeoutError:
                # Check if the task is still running
                if task.done():
                    break
                continue
            except WebSocketDisconnect:
                print(f"🔌 WebSocket disconnected: flow_id={flow_id}")
                break
    except Exception as e:
        print(f"❌ WebSocket error for flow_id={flow_id}: {e}")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
