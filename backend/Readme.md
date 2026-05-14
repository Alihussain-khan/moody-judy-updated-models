# Moody Judy (backend)

FastAPI backend for audio-based emotion pipeline (convert(audio) → ASR(transcripts) → SER(MSP, Wav2vec, wavlm) → Claude summary).

## Requirements

- Python
- `ffmpeg` installed and on PATH (run `ffmpeg -version` to verify)

## Setup (one command at a time)

From the `backend/` folder:

1) Create venv

```sh
python -m venv .venv
```

2) Activate venv

Windows (PowerShell):

```sh
.venv\Scripts\Activate.ps1
```

macOS/Linux (bash/zsh):

```sh
source .venv/bin/activate
```

3) Upgrade pip

```sh
python -m pip install -U pip
```

4) Install dependencies

```sh
pip install -r requirements.txt
```

## Configure (optional)

Copy `.env.example` to `.env`, add allowed cors here(important).then edit values if needed.

## Run

```sh
fastapi dev app/main.py #enter path according to your terminal
```

Health:

```sh
curl http://127.0.0.1:8000/health
```

## API

Base prefix: `/v1`

### 1) Run all (upload + full pipeline)

- `POST /v1/jobs/run-all` (multipart/form-data)
	- fields: `file`, `claude_api_key`, optional `claude_model`

Example:

```sh
curl -X POST http://127.0.0.1:8000/v1/jobs/run-all -F "file=@path/to/audio.wav" -F "claude_api_key=YOUR_KEY" -F "claude_model=claude-3-5-sonnet-latest"
```

### 2) Events (progress stream)

- `GET /v1/jobs/{job_id}/events` (Server-Sent Events)

Example:

```sh
curl -N http://127.0.0.1:8000/v1/jobs/{job_id}/events
```

### 3) Result

- `GET /v1/jobs/{job_id}/result` (returns `final.json` when ready)

Example:

```sh
curl http://127.0.0.1:8000/v1/jobs/{job_id}/result
```