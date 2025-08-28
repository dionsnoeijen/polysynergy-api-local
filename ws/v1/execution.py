import asyncio
import os

from fastapi import WebSocket, APIRouter, WebSocketDisconnect
import redis.asyncio as redis

router = APIRouter()
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
redis_client = redis.from_url(
    redis_url,
    decode_responses=True,
    db=0
)

@router.websocket("/execution/{flow_id}")
async def execution_ws(websocket: WebSocket, flow_id: str):
    await websocket.accept()
    print('ACCEPTED CONNECTION')

    exec_channel = f"execution_updates:{flow_id}"
    chat_channel = f"chat_stream:{flow_id}"

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(exec_channel, chat_channel)

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
            await pubsub.unsubscribe(exec_channel, chat_channel)
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
