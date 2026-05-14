# app/services/ser_wav2vec_large.py
from __future__ import annotations
import time
from pathlib import Path
import torch
import soundfile as sf
import numpy as np
from scipy.signal import resample_poly
from transformers import pipeline

_MODEL_ID = "superb/wav2vec2-large-superb-er"

_clf = None

def _get_pipe():
    global _clf
    if _clf is None:
        _clf = pipeline(
            task="audio-classification",
            model=_MODEL_ID,
            device=0 if torch.cuda.is_available() else -1,
        )
    return _clf

def _load_audio(path: Path, target_sr: int = 16000):
    x, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if getattr(x, "ndim", 1) == 2:
        x = x.mean(axis=1)
    if sr != target_sr:
        g = np.gcd(sr, target_sr)
        x = resample_poly(x, target_sr // g, sr // g).astype("float32")
        sr = target_sr
    return x, sr

def run_ser_wav2vec_large(wav_path: Path) -> dict:
    t0 = time.time()
    pipe = _get_pipe()
    x, sr = _load_audio(wav_path, 16000)
    preds = pipe({"array": x, "sampling_rate": sr})

    top = preds[0]
    return {
        "model": _MODEL_ID,
        "sampling_rate": sr,
        "top_label": top["label"],
        "top_score": float(top["score"]),
        "scores": [{"label": p["label"], "score": float(p["score"])} for p in preds],
        "took_s": round(time.time() - t0, 3),
    }