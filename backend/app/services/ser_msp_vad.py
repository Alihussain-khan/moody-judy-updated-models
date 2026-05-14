from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn
from transformers import Wav2Vec2Processor
from transformers.models.wav2vec2.modeling_wav2vec2 import (
    Wav2Vec2Model,
    Wav2Vec2PreTrainedModel,
)
from app.services.vad_mapping import vad_to_polarity

MODEL_ID = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
DEVICE = "cpu"
TARGET_SR = 16000 


class RegressionHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features):
        x = self.dropout(features)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)
        return x


class EmotionModel(Wav2Vec2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.init_weights()

    def forward(self, input_values):
        outputs = self.wav2vec2(input_values)
        hidden_states = outputs.last_hidden_state
        pooled = hidden_states.mean(dim=1)     
        logits = self.classifier(pooled)
        return pooled, logits



EmotionModel.all_tied_weights_keys = {}
EmotionModel._tied_weights_keys = []


_processor: Wav2Vec2Processor | None = None
_model: EmotionModel | None = None


def _load() -> tuple[Wav2Vec2Processor, EmotionModel]:
    global _processor, _model
    if _processor is None or _model is None:
        _processor = Wav2Vec2Processor.from_pretrained(MODEL_ID)
        _model = EmotionModel.from_pretrained(MODEL_ID).to(DEVICE)
        _model.eval()
    return _processor, _model


def _load_audio_16k_mono(path: Path) -> np.ndarray:

    x, sr = sf.read(str(path), always_2d=False)
    if isinstance(x, np.ndarray) and x.ndim == 2:
        x = x.mean(axis=1)
    x = np.asarray(x, dtype=np.float32)

    if sr != TARGET_SR:

        raise RuntimeError(f"Expected {TARGET_SR} Hz WAV, got {sr} Hz for {path.name}")

    return x


def run_ser_msp_vad(wav_path: Path) -> Dict[str, Any]:
    t0 = time.time()

    x = _load_audio_16k_mono(wav_path)
    processor, model = _load()

    inputs = processor(x, sampling_rate=TARGET_SR, return_tensors="pt")
    input_values = inputs["input_values"].to(DEVICE)

    with torch.inference_mode():
        _emb, vad = model(input_values) 

    vad = vad.cpu().numpy()[0].astype(float)


    vad_raw = {
        "arousal": float(vad[0]),
        "dominance": float(vad[1]),
        "valence": float(vad[2]),
    }
    polarity_hint = vad_to_polarity(vad_raw)
    return {
        "model": MODEL_ID,
        "sampling_rate": TARGET_SR,
        "vad_raw": vad_raw,
        "polarity_hint": polarity_hint,
        "took_s": round(time.time() - t0, 3),
    }