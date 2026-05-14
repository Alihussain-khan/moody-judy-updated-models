from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

MODEL_ID = "iic/emotion2vec_plus_large"

_model = None


def _load():
    global _model
    if _model is None:
        from funasr import AutoModel  # pip install funasr
        _model = AutoModel(model=MODEL_ID)
    return _model


def run_ser_emotion2vec(wav_path: Path) -> Dict[str, Any]:
    t0 = time.time()
    model = _load()

    res = model.generate(
        str(wav_path),
        output_dir=None,
        granularity="utterance",
        extract_embedding=False,
    )

    entry = res[0]
    labels: list = entry.get("labels", [])
    scores: list = [float(s) for s in entry.get("scores", [])]

    score_list = [{"label": l, "score": s} for l, s in zip(labels, scores)]
    score_list.sort(key=lambda d: d["score"], reverse=True)
    top = score_list[0] if score_list else {"label": "unknown", "score": 0.0}

    return {
        "model": MODEL_ID,
        "top_label": top["label"],
        "top_score": top["score"],
        "scores": score_list,
        "took_s": round(time.time() - t0, 3),
    }
