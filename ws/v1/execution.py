from fastapi import WebSocket, APIRouter, WebSocketDisconnect
import redis.asyncio as redis

router = APIRouter()
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

@router.websocket("/execution/{flow_id}")
async def execution_ws(websocket: WebSocket, flow_id: str):
    await websocket.accept()
    channel = f"execution_updates:{flow_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: flow_id={flow_id}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()