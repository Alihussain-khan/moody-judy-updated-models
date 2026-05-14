from __future__ import annotations
import asyncio
import time
from collections import defaultdict
from typing import Any, Dict, Optional

_queues = defaultdict(asyncio.Queue)

async def emit(job_id: str, message: str, stage: Optional[str] = None) -> None:
    await _queues[job_id].put({
        "ts": time.time(),
        "job_id": job_id,
        "stage": stage,
        "message": message,
    })

async def close(job_id: str) -> None:
    await _queues[job_id].put({"event": "close"})

async def next_event(job_id: str) -> Dict[str, Any]:
    return await _queues[job_id].get()