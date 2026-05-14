import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.services.events import next_event
from app.services.jobs import get_job

router = APIRouter()

@router.get("/jobs/{job_id}/events")
async def events(job_id: str):
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    async def gen():
        yield {"event": "message", "data": json.dumps({"message": "connected", "job_id": job_id})}
        while True:
            item = await next_event(job_id)
            if item.get("event") == "close":
                break
            yield {"event": "message", "data": json.dumps(item)}

    return EventSourceResponse(gen())