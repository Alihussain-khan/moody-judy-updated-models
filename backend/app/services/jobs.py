from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any
from app.services.transcribe import transcribe_wav
from app.services.events import emit, close
from app.services.audio_convert import convert_to_wav_mono_16k
from app.services.storage import job_dir
from app.services.ser_emotion2vec import run_ser_emotion2vec
from app.services.acoustic_beats import run_acoustic_beats
from app.services.acoustic_clap import run_acoustic_clap
from app.services.llm_claude import call_claude

_jobs: Dict[str, Dict[str, Any]] = {}

def get_job(job_id: str) -> Dict[str, Any] | None:
    return _jobs.get(job_id)

def _write_job_meta(job_id: str) -> None:
    d = job_dir(job_id)
    meta_path = d / "job.json"
    meta_path.write_text(json.dumps(_jobs[job_id], indent=2), encoding="utf-8")

async def run_phase0_convert(job_id: str) -> None:
    """
    Phase 0:
    - emit "converting..."
    - convert to wav
    - emit "done: file"
    """
    try:
        _jobs[job_id]["status"] = "converting"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "Converting…", stage="convert")

        src = Path(_jobs[job_id]["src_path"])
        wav = Path(_jobs[job_id]["wav_path"])

        await asyncio.to_thread(convert_to_wav_mono_16k, src, wav)

        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["updated_at"] = time.time()
        _jobs[job_id]["wav_ready"] = True
        _write_job_meta(job_id)

        await emit(job_id, f"Done: {wav.name}", stage="convert")

    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, f"Error: {e}", stage="error")


def create_job(job_id: str, filename: str, src_path: Path, wav_path: Path) -> Dict[str, Any]:
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "filename": filename,
        "src_path": str(src_path),
        "wav_path": str(wav_path),
        "wav_ready": False,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
        "transcript_ready": False,
        "emotion2vec_ready": False,
        "emotion2vec_path": None,
        "beats_ready": False,
        "beats_path": None,
        "clap_ready": False,
        "clap_path": None,
        "claude_ready": False,
        "claude_path": None,
        "final_ready": False,
        "final_path": None,
    }
    _write_job_meta(job_id)
    return _jobs[job_id]


async def run_phase1_transcribe(job_id: str) -> None:
    try:
        wav = Path(_jobs[job_id]["wav_path"])
        result = await asyncio.to_thread(transcribe_wav, wav)

        transcript_path = job_dir(job_id) / "transcript.json"
        transcript_path.write_text(json.dumps(result, indent=2))

        _jobs[job_id]["transcript_ready"] = True
        _write_job_meta(job_id)

    except Exception as e:
        if _jobs.get(job_id):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["updated_at"] = time.time()
            _write_job_meta(job_id)
        await emit(job_id, f"Error: {e}", stage="error")


async def run_phase2_emotion2vec(job_id: str) -> None:
    try:
        if not _jobs.get(job_id):
            return
        if not _jobs[job_id].get("wav_ready"):
            raise RuntimeError("WAV not ready yet. Convert first.")

        _jobs[job_id]["status"] = "ser_emotion2vec"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "SER (emotion2vec+) started…", stage="ser")

        wav = Path(_jobs[job_id]["wav_path"])
        out_path = job_dir(job_id) / "ser__iic__emotion2vec_plus_large.json"

        result = await asyncio.to_thread(run_ser_emotion2vec, wav)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        _jobs[job_id]["emotion2vec_ready"] = True
        _jobs[job_id]["emotion2vec_path"] = str(out_path)
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "SER (emotion2vec+) done.", stage="ser")

    except Exception as e:
        if _jobs.get(job_id):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["updated_at"] = time.time()
            _write_job_meta(job_id)
        await emit(job_id, f"Error: {e}", stage="error")


async def run_phase3_beats(job_id: str) -> None:
    try:
        if not _jobs.get(job_id):
            return
        if not _jobs[job_id].get("wav_ready"):
            raise RuntimeError("WAV not ready yet. Convert first.")

        _jobs[job_id]["status"] = "beats"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "BEATs acoustic analysis started…", stage="beats")

        wav = Path(_jobs[job_id]["wav_path"])
        out_path = job_dir(job_id) / "acoustic__beats_iter3_plus.json"

        result = await asyncio.to_thread(run_acoustic_beats, wav)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        _jobs[job_id]["beats_ready"] = True
        _jobs[job_id]["beats_path"] = str(out_path)
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "BEATs acoustic analysis done.", stage="beats")

    except Exception as e:
        if _jobs.get(job_id):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["updated_at"] = time.time()
            _write_job_meta(job_id)
        await emit(job_id, f"Error: {e}", stage="error")


async def run_phase3_clap(job_id: str) -> None:
    try:
        if not _jobs.get(job_id):
            return
        if not _jobs[job_id].get("wav_ready"):
            raise RuntimeError("WAV not ready yet. Convert first.")

        _jobs[job_id]["status"] = "clap"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "CLAP acoustic analysis started…", stage="clap")

        wav = Path(_jobs[job_id]["wav_path"])
        out_path = job_dir(job_id) / "acoustic__clap_htsat_fused.json"

        result = await asyncio.to_thread(run_acoustic_clap, wav)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        _jobs[job_id]["clap_ready"] = True
        _jobs[job_id]["clap_path"] = str(out_path)
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "CLAP acoustic analysis done.", stage="clap")

    except Exception as e:
        if _jobs.get(job_id):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["updated_at"] = time.time()
            _write_job_meta(job_id)
        await emit(job_id, f"Error: {e}", stage="error")


async def run_claude_phase(job_id: str, api_key: str, model: str | None = None) -> dict:
    if job_id not in _jobs:
        raise ValueError("Job not found")

    job = _jobs[job_id]

    if not job.get("wav_ready"):
        raise RuntimeError("WAV not ready")

    if not job.get("transcript_ready"):
        await run_phase1_transcribe(job_id)
        if not job.get("transcript_ready"):
            raise RuntimeError(f"ASR failed: {job.get('error', 'unknown')}")

    if not job.get("emotion2vec_ready"):
        await run_phase2_emotion2vec(job_id)
        if not job.get("emotion2vec_ready"):
            raise RuntimeError(f"emotion2vec failed: {job.get('error', 'unknown')}")

    if not job.get("beats_ready"):
        await run_phase3_beats(job_id)
        if not job.get("beats_ready"):
            raise RuntimeError(f"BEATs failed: {job.get('error', 'unknown')}")

    if not job.get("clap_ready"):
        await run_phase3_clap(job_id)
        if not job.get("clap_ready"):
            raise RuntimeError(f"CLAP failed: {job.get('error', 'unknown')}")

    jdir = job_dir(job_id)

    transcript = json.loads((jdir / "transcript.json").read_text())
    emotion2vec = json.loads((jdir / "ser__iic__emotion2vec_plus_large.json").read_text())
    beats = json.loads((jdir / "acoustic__beats_iter3_plus.json").read_text())
    clap = json.loads((jdir / "acoustic__clap_htsat_fused.json").read_text())

    bundle = {
        "transcript": transcript["text"],
        "ser_emotion2vec": emotion2vec,
        "acoustic_beats": beats,
        "acoustic_clap": clap,
    }

    result = call_claude(api_key, bundle, model)

    out_path = jdir / "claude.json"
    out_path.write_text(json.dumps(result, indent=2))

    job["claude_ready"] = True
    job["claude_path"] = str(out_path)

    _write_job_meta(job_id)

    return result


async def run_all_pipeline(
    job_id: str,
    claude_api_key: str,
    claude_model: str | None = None,
) -> None:
    """
    Full pipeline:
    convert -> asr -> emotion2vec -> beats -> clap -> claude -> final.json
    Streams progress via SSE.
    """
    try:
        if job_id not in _jobs:
            return

        # ---------- Convert ----------
        await run_phase0_convert(job_id)
        if not _jobs[job_id].get("wav_ready"):
            raise RuntimeError("Conversion failed (wav not ready).")

        # ---------- ASR ----------
        _jobs[job_id]["status"] = "asr"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "ASR started…", stage="asr")
        await run_phase1_transcribe(job_id)
        if not _jobs[job_id].get("transcript_ready"):
            raise RuntimeError(f"ASR failed: {_jobs[job_id].get('error', 'unknown')}")
        await emit(job_id, "ASR done.", stage="asr")

        # ---------- SER: emotion2vec+ ----------
        _jobs[job_id]["status"] = "ser_emotion2vec"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await run_phase2_emotion2vec(job_id)
        if not _jobs[job_id].get("emotion2vec_ready"):
            raise RuntimeError(f"emotion2vec failed: {_jobs[job_id].get('error', 'unknown')}")

        # ---------- Acoustic: BEATs ----------
        _jobs[job_id]["status"] = "beats"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await run_phase3_beats(job_id)
        if not _jobs[job_id].get("beats_ready"):
            raise RuntimeError(f"BEATs failed: {_jobs[job_id].get('error', 'unknown')}")

        # ---------- Acoustic: CLAP ----------
        _jobs[job_id]["status"] = "clap"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await run_phase3_clap(job_id)
        if not _jobs[job_id].get("clap_ready"):
            raise RuntimeError(f"CLAP failed: {_jobs[job_id].get('error', 'unknown')}")

        # ---------- Claude ----------
        _jobs[job_id]["status"] = "claude"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "Claude started…", stage="llm")

        result = await run_claude_phase(job_id, claude_api_key, claude_model)

        # ---------- Final ----------
        jdir = job_dir(job_id)
        final_path = jdir / "final.json"
        final_payload = {
            "job_id": job_id,
            "final": result,
            "paths": {
                "transcript": str(jdir / "transcript.json"),
                "ser_emotion2vec": _jobs[job_id].get("emotion2vec_path"),
                "acoustic_beats": _jobs[job_id].get("beats_path"),
                "acoustic_clap": _jobs[job_id].get("clap_path"),
                "claude": _jobs[job_id].get("claude_path"),
            },
        }
        final_path.write_text(json.dumps(final_payload, indent=2), encoding="utf-8")

        _jobs[job_id]["final_ready"] = True
        _jobs[job_id]["final_path"] = str(final_path)
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["updated_at"] = time.time()
        _write_job_meta(job_id)

        await emit(job_id, "Final ready.", stage="final")

    except Exception as e:
        if _jobs.get(job_id):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["updated_at"] = time.time()
            _write_job_meta(job_id)

        await emit(job_id, f"Error: {e}", stage="error")

    finally:
        await close(job_id)
