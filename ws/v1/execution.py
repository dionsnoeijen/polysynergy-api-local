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
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except asyncio.CancelledError:
            print(f"🛑 Forward task cancelled for flow_id={flow_id}")
            # Force close pubsub to break the `async for`
            await pubsub.unsubscribe(exec_channel, chat_channel)
            await pubsub.close()
            raise  # ← nodig om de shutdown door te zetten

    task = asyncio.create_task(forward_messages())
    try:
        await task
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: flow_id={flow_id}")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
