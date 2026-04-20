# aicore Production Guide

Single-service FastAPI stack for OCR + ASR + Ollama parsing.

## Architecture

- One FastAPI service (`aicore.api_server`) with model preloading at startup.
- Inference requests are serialized through a bounded GPU queue.
- Queue workers execute `pipeline.process_image/process_audio/process_text`.
- Image OCR output is re-parsed by Ollama using `OCR_PROMPT_2`.

## Key Production Behavior

- Endpoints: `/api/process/image`, `/api/process/audio`, `/api/process/text`
- Readiness probes: `/health/live`, `/health/ready`
- Every response includes:
  - `request_id`
  - `queue_wait_ms`
  - `latency_ms`

## Environment Variables

Copy `.env.example` to `.env` and set values for your VPS.

Important knobs:

- `AICORE_GPU_WORKERS` (default `1`)
- `AICORE_GPU_QUEUE_MAXSIZE` (default `64`)
- `AICORE_REQUEST_TIMEOUT_SEC` (default `120`)
- `AICORE_MAX_IMAGE_MB` (default `10`)
- `AICORE_MAX_AUDIO_MB` (default `20`)
- `OLLAMA_HOST`, `OLLAMA_API_KEY`, `OLLAMA_MODEL`

## Deploy On VPS (Conda + systemd)

### 1) Prepare project

```bash
git clone <repo> /opt/slacker-ai
cd /opt/slacker-ai
cp .env.example .env
```

### 2) Create/Update Conda env

```bash
bash scripts/deploy_conda_vps.sh
```

### 3) Install systemd service

```bash
sudo cp deploy/systemd/slacker-aicore.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now slacker-aicore
sudo systemctl status slacker-aicore
```

### 4) Configure nginx reverse proxy

```bash
sudo cp deploy/nginx/slacker-aicore.conf /etc/nginx/sites-available/slacker-aicore
sudo ln -s /etc/nginx/sites-available/slacker-aicore /etc/nginx/sites-enabled/slacker-aicore
sudo nginx -t
sudo systemctl reload nginx
```

## Uvicorn Recommendation

Use one Uvicorn worker per GPU process:

```bash
python -m uvicorn aicore.api_server:app --host 0.0.0.0 --port 8000 --workers 1
```

Scale through queue + bigger GPU or horizontal replicas behind nginx, not by spawning many workers on a single GPU by default.
