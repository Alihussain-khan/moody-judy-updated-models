from __future__ import annotations
import shutil
import uuid
from pathlib import Path

from app.core.config import settings

def new_job_id() -> str:
    return uuid.uuid4().hex

def save_upload(job_id: str, filename: str, fileobj) -> Path:
    ext = Path(filename).suffix.lower() or ".bin"
    src_path = settings.UPLOADS_DIR / f"{job_id}.src{ext}"
    with src_path.open("wb") as f:
        shutil.copyfileobj(fileobj, f)
    return src_path

def job_dir(job_id: str) -> Path:
    d = settings.JOBS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def wav_path(job_id: str) -> Path:
    return settings.UPLOADS_DIR / f"{job_id}.wav"