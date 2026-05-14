from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import soundfile as sf
import torch

# ---------- paths ----------
BEATS_REPO_DIR = Path(r"E:\msds\thesis\unilm\beats")
BEATS_CKPT = Path(
    r"C:\Users\Ali Khan\.cache\huggingface\hub"
    r"\models--THUdyh--Ola_speech_encoders\snapshots"
    r"\40111b936c8ab76f52d9f7d641adafc59f87fc41"
    r"\BEATs_iter3_plus_AS2M_finetuned_on_AS2M_cpt2.pt"
)
ONTOLOGY_URL = "https://raw.githubusercontent.com/audioset/ontology/master/ontology.json"
# cache in backend/data/ — NOT inside the source tree, so uvicorn watchfiles
# does not detect the write and restart the server mid-pipeline
_ONTOLOGY_CACHE = Path(__file__).parent.parent.parent / "data" / "_audioset_ontology.json"
TOP_K = 5

# ---------- lazy globals ----------
_beats_model = None
_label_dict: dict | None = None
_beats_device: str | None = None
_id_to_name: dict | None = None


def _load_ontology() -> dict:
    global _id_to_name
    if _id_to_name is not None:
        return _id_to_name

    if _ONTOLOGY_CACHE.exists():
        _id_to_name = json.loads(_ONTOLOGY_CACHE.read_text(encoding="utf-8"))
        return _id_to_name

    import requests
    resp = requests.get(ONTOLOGY_URL, timeout=15)
    resp.raise_for_status()
    ontology = resp.json()
    _id_to_name = {item["id"]: item["name"] for item in ontology}
    _ONTOLOGY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _ONTOLOGY_CACHE.write_text(
        json.dumps(_id_to_name, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return _id_to_name


def _load_beats():
    global _beats_model, _label_dict, _beats_device
    if _beats_model is not None:
        return _beats_model, _label_dict, _beats_device

    if str(BEATS_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(BEATS_REPO_DIR))

    from BEATs import BEATs, BEATsConfig  # noqa: N811

    _beats_device = "cuda" if torch.cuda.is_available() else "cpu"
    ckpt = torch.load(str(BEATS_CKPT), map_location="cpu", weights_only=False)
    cfg = BEATsConfig(ckpt["cfg"])
    model = BEATs(cfg)
    model.load_state_dict(ckpt["model"])
    model.eval()
    model.to(_beats_device)

    _beats_model = model
    _label_dict = ckpt.get("label_dict", {})
    return _beats_model, _label_dict, _beats_device


def run_acoustic_beats(wav_path: Path) -> Dict[str, Any]:
    t0 = time.time()

    model, label_dict, device = _load_beats()
    id_to_name = _load_ontology()

    audio, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if sr != 16000:
        raise RuntimeError(f"Expected 16 kHz audio, got {sr} Hz — run convert phase first.")

    wav_t = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)
    pad = torch.zeros(wav_t.shape, dtype=torch.bool).to(device)

    with torch.no_grad():
        out, _ = model.extract_features(wav_t, padding_mask=pad)

    # Fine-tuned model returns probs [B, C]; non-finetuned returns [B, T, D]
    if out.ndim == 2:
        probs = out[0].cpu().numpy().astype(np.float32)
    elif out.ndim == 3:
        probs = out[0].mean(dim=0).cpu().numpy().astype(np.float32)
    else:
        raise RuntimeError(f"Unexpected BEATs output shape: {tuple(out.shape)}")

    k = min(TOP_K, len(probs))
    vals, idxs = torch.topk(torch.tensor(probs), k=k)
    top_k = []
    for score, idx in zip(vals.tolist(), idxs.tolist()):
        label_id = label_dict.get(idx, str(idx))
        name = id_to_name.get(label_id, label_id)
        top_k.append({"id": label_id, "label": name, "score": round(float(score), 5)})

    return {
        "model": "BEATs_iter3_plus_AS2M_finetuned_on_AS2M_cpt2",
        "top_label": top_k[0]["label"] if top_k else None,
        "top_score": top_k[0]["score"] if top_k else None,
        "top_k": top_k,
        "took_s": round(time.time() - t0, 3),
    }
