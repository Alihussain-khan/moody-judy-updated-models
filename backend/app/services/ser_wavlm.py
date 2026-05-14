from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from scipy.io import wavfile
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

MODEL_ID = "jihedjabnoun/wavlm-base-emotion"

_extractor = None
_model = None

def _load():
    global _extractor, _model
    if _extractor is None or _model is None:
        _extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        _model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)
        _model.eval()
    return _extractor, _model

def _to_float32_mono(x: np.ndarray) -> np.ndarray:
    if x.ndim == 2:
        x = x.mean(axis=1)
    if np.issubdtype(x.dtype, np.integer):
        max_val = np.iinfo(x.dtype).max
        x = x.astype(np.float32) / float(max_val)
    else:
        x = x.astype(np.float32)
    return x

def run_ser_wavlm(wav_path: Path) -> Dict[str, Any]:
    t0 = time.time()

    sr, audio = wavfile.read(str(wav_path))
    audio = _to_float32_mono(audio)

    extractor, model = _load()

    inputs = extractor(audio, sampling_rate=sr, return_tensors="pt", padding=True)

    with torch.no_grad():
        logits = model(**inputs).logits.squeeze(0)

    probs = torch.softmax(logits, dim=-1).cpu().numpy()
    id2label = model.config.id2label

    scores: List[Dict[str, Any]] = [
        {"label": id2label.get(i, str(i)), "score": float(p)}
        for i, p in enumerate(probs.tolist())
    ]
    scores.sort(key=lambda d: d["score"], reverse=True)
    top = scores[0]

    return {
        "model": MODEL_ID,
        "sampling_rate": int(sr),
        "top_label": top["label"],
        "top_score": top["score"],
        "scores": scores,
        "took_s": round(time.time() - t0, 3),
    }