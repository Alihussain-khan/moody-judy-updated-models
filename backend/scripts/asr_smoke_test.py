from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")

audio_path = r"data\uploads\test.wav"  # change to an actual file you have
segments, info = model.transcribe(audio_path, vad_filter=True)

print("language:", info.language)
print("duration:", info.duration)

text = "".join(seg.text for seg in segments).strip()
print("\nTEXT:\n", text)