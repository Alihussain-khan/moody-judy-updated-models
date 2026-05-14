import asyncio
from pathlib import Path
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Form
from app.services.jobs import (
    create_job,
    run_phase0_convert,
    get_job,
    run_phase1_transcribe,
    run_phase2_emotion2vec,
    run_phase3_beats,
    run_phase3_clap,
    run_claude_phase,
    run_all_pipeline,
)
from app.services.storage import new_job_id, save_upload, wav_path

router = APIRouter()


@router.post("/jobs")
async def create(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    job_id = new_job_id()
    src = save_upload(job_id, file.filename, file.file)
    wav = wav_path(job_id)

    create_job(job_id, file.filename, src, wav)

    asyncio.create_task(run_phase0_convert(job_id))

    return {
        "job_id": job_id,
        "status_url": f"/v1/jobs/{job_id}",
        "events_url": f"/v1/jobs/{job_id}/events",
    }


@router.get("/jobs/{job_id}")
def status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/transcribe")
async def transcribe(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    asyncio.create_task(run_phase1_transcribe(job_id))
    return {
        "job_id": job_id,
        "status_url": f"/v1/jobs/{job_id}",
        "events_url": f"/v1/jobs/{job_id}/events",
    }


@router.post("/jobs/{job_id}/ser/emotion2vec")
async def ser_emotion2vec(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    asyncio.create_task(run_phase2_emotion2vec(job_id))
    return {
        "job_id": job_id,
        "status_url": f"/v1/jobs/{job_id}",
        "events_url": f"/v1/jobs/{job_id}/events",
    }


@router.post("/jobs/{job_id}/acoustic/beats")
async def acoustic_beats(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    asyncio.create_task(run_phase3_beats(job_id))
    return {
        "job_id": job_id,
        "status_url": f"/v1/jobs/{job_id}",
        "events_url": f"/v1/jobs/{job_id}/events",
    }


@router.post("/jobs/{job_id}/acoustic/clap")
async def acoustic_clap(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    asyncio.create_task(run_phase3_clap(job_id))
    return {
        "job_id": job_id,
        "status_url": f"/v1/jobs/{job_id}",
        "events_url": f"/v1/jobs/{job_id}/events",
    }


@router.post("/jobs/{job_id}/claude")
async def run_claude(job_id: str, body: dict = Body(...)):
    api_key = body.get("api_key")
    model = body.get("model")

    if not api_key:
        raise HTTPException(status_code=400, detail="Missing api_key")

    try:
        result = await run_claude_phase(job_id, api_key, model)
        return result
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/run-all")
async def run_all(
    file: UploadFile = File(...),
    claude_api_key: str = Form(...),
    claude_model: str | None = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    job_id = new_job_id()
    src = save_upload(job_id, file.filename, file.file)
    wav = wav_path(job_id)

    create_job(job_id, file.filename, src, wav)

    asyncio.create_task(run_all_pipeline(job_id, claude_api_key, claude_model))

    return {
        "job_id": job_id,
        "status_url": f"/v1/jobs/{job_id}",
        "events_url": f"/v1/jobs/{job_id}/events",
        "result_url": f"/v1/jobs/{job_id}/result",
    }


@router.get("/jobs/{job_id}/result")
def get_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get("final_ready"):
        raise HTTPException(status_code=404, detail="Result not ready")

    p = Path(job["final_path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="Result file missing")

    return json.loads(p.read_text(encoding="utf-8"))
