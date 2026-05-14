from faster_whisper import WhisperModel
from pathlib import Path

_model = WhisperModel("large-v3", device="cpu", compute_type="int8")

def transcribe_wav(wav_path: Path) -> dict:
    segments, info = _model.transcribe(str(wav_path), vad_filter=True)
    text = "".join(s.text for s in segments).strip()
    return {"text": text}