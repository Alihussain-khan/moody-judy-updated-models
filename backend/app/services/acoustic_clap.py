from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly
from transformers import ClapModel, ClapProcessor

CLAP_SR = 48000  # ClapFeatureExtractor native rate — must resample manually in transformers 5.x

MODEL_ID = "laion/clap-htsat-fused"

# Zero-shot prompts phrased as acoustic scene descriptions.
# CLAP was trained on audio-caption pairs, so scene-style text works better
# than bare emotion words.
EMOTION_PROMPTS = [
    "happy joyful laughter and cheerful speech",
    "sad sorrowful crying and distressed speech",
    "angry shouting and aggressive frustrated speech",
    "fearful scared and anxious speech",
    "calm quiet neutral speech",
    "excited energetic enthusiastic speech",
    "disgusted and contemptuous voice",
    "surprised and astonished voice",
]

_model: ClapModel | None = None
_processor: ClapProcessor | None = None
_clap_device: str | None = None


def _load():
    global _model, _processor, _clap_device
    if _model is None:
        _processor = ClapProcessor.from_pretrained(MODEL_ID)
        _model = ClapModel.from_pretrained(MODEL_ID)
        _model.eval()
        _clap_device = "cuda" if torch.cuda.is_available() else "cpu"
        _model.to(_clap_device)
    return _model, _processor


def run_acoustic_clap(wav_path: Path) -> Dict[str, Any]:
    t0 = time.time()

    model, processor = _load()

    audio, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    # transformers 5.x ClapFeatureExtractor requires 48 kHz input — resample manually
    if sr != CLAP_SR:
        g = int(np.gcd(sr, CLAP_SR))
        audio = resample_poly(audio, CLAP_SR // g, sr // g).astype(np.float32)
        sr = CLAP_SR

    inputs = processor(
        text=EMOTION_PROMPTS,
        audio=audio,
        sampling_rate=sr,
        return_tensors="pt",
        padding=True,
    )
    inputs = {k: v.to(_clap_device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    # logits_per_audio: (1, num_texts) — softmax gives relative similarity
    probs = torch.softmax(outputs.logits_per_audio, dim=-1)[0].cpu().numpy()

    scores = [
        {"label": prompt, "score": round(float(p), 5)}
        for prompt, p in zip(EMOTION_PROMPTS, probs)
    ]
    scores.sort(key=lambda d: d["score"], reverse=True)

    return {
        "model": MODEL_ID,
        "top_label": scores[0]["label"],
        "top_score": scores[0]["score"],
        "scores": scores,
        "took_s": round(time.time() - t0, 3),
    }
