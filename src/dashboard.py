import os
import json
import asyncio
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow your Lovable frontend to connect from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track dismissed alarms in memory
dismissed_alarms = set()

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_CHANNEL = 'icu_vitals'


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/dismiss/{subject_id}")
async def dismiss_alarm(subject_id: str):
    dismissed_alarms.add(subject_id)
    return {"status": "dismissed", "subject_id": subject_id}


@app.delete("/dismiss/{subject_id}")
async def undismiss_alarm(subject_id: str):
    dismissed_alarms.discard(subject_id)
    return {"status": "active", "subject_id": subject_id}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("Frontend connected via WebSocket")

    r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT,
                       decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])

                # If this patient's alarm was dismissed, mark it
                if data['subject_id'] in dismissed_alarms:
                    data['warning'] = 0
                    data['dismissed'] = True
                else:
                    data['dismissed'] = False

                await ws.send_json(data)

    except WebSocketDisconnect:
        print("Frontend disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(REDIS_CHANNEL)
        await r.aclose()