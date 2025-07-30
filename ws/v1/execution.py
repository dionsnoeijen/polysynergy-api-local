import asyncio

from fastapi import WebSocket, APIRouter, WebSocketDisconnect
import redis.asyncio as redis

router = APIRouter()
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

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
            pass

    task = asyncio.create_task(forward_messages())
    try:
        await task
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: flow_id={flow_id}")
    finally:
        task.cancel()
        await pubsub.unsubscribe(exec_channel, chat_channel)
        await pubsub.close()
