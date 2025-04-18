"""
FastAPI Integration Example for redisaq: Job Enqueue

This script runs a FastAPI application that enqueues email messages to the 'send_email' topic.
The consumer is run separately in 'consumer.py' to process messages in a different process.

Endpoints:
- POST /messages: Enqueue a batch of email messages.
- GET /status: Check Redis connection status.

Prerequisites:
- Python 3.8+ and dependencies installed (`pip install redisaq fastapi uvicorn`).
- Redis running at redis://localhost:6379.

How to Run:
1. Start Redis:
   ```bash
   docker-compose up -d
   ```
2. Run Consumer (in one terminal):
   ```bash
   python consumer.py
   ```
3. Run FastAPI App (in another terminal):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. Test Endpoints:
   ```bash
   curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"messages": [{"to": "user1@example.com", "subject": "Test", "body": "Hello"}]}'
   curl http://localhost:8000/status
   ```
5. Stop with Ctrl+C, then:
   ```bash
   docker-compose down
   ```

Expected Behavior:
- Enqueues messages to 'send_email' topic via /messages endpoint.
- /status endpoint confirms Redis connectivity.
- Limits streams to maxlen=1000 using xadd.
"""

import logging
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from redisaq import Producer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Producer instance
producer = Producer(topic="send_email", redis_url="redis://localhost:6379", maxlen=1000)

@app.on_event("startup")
async def startup_event():
    await producer.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await producer.close()

class JobPayload(BaseModel):
    to: str
    subject: str
    body: str

class EnqueueRequest(BaseModel):
    jobs: List[JobPayload]

@app.post("/jobs")
async def enqueue_jobs(request: EnqueueRequest):
    payloads = [job.model_dump() for job in request.jobs]
    job_ids = await producer.batch_enqueue(payloads)
    return {"job_ids": job_ids}

@app.get("/status")
async def get_status():
    try:
        await producer.redis.ping()
        return {"redis": "connected"}
    except Exception as e:
        return {"redis": f"error: {str(e)}"}