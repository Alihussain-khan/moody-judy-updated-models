from __future__ import annotations

import subprocess
from pathlib import Path

def convert_to_wav_mono_16k(src_path: Path, dst_wav: Path) -> None:
    """
    Convert any audio file to PCM WAV, mono, 16kHz using ffmpeg.
    Works on Python 3.13+ without pydub/audioop.
    Requires `ffmpeg` available on PATH.
    """
    src_path = Path(src_path)
    dst_wav = Path(dst_wav)
    dst_wav.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                    # overwrite output
        "-i", str(src_path),     # input
        "-ac", "1",              # mono
        "-ar", "16000",          # 16 kHz
        "-c:a", "pcm_s16le",     # 16-bit PCM
        str(dst_wav),
    ]

    # capture output for debugging, but DO NOT print unless error
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError(
            "ffmpeg conversion failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"STDERR:\n{proc.stderr.strip()}"
        )