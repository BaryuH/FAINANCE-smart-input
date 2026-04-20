"""Production FastAPI backend for Slacker AI core."""

import asyncio
import logging
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import (
    ALLOWED_ORIGINS,
    GPU_QUEUE_MAXSIZE,
    GPU_WORKERS,
    LOG_FORMAT,
    LOG_LEVEL,
    MAX_AUDIO_MB,
    MAX_IMAGE_MB,
    REQUEST_TIMEOUT_SEC,
    SERVER_HOST,
    SERVER_PORT,
    SERVER_RELOAD,
    UVICORN_WORKERS,
)
from .pipeline import AIPipeline
from .runtime.gpu_queue import GpuTaskQueue

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

MB = 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AI server - loading all models...")
    pipeline = AIPipeline()
    gpu_queue = GpuTaskQueue(
        worker_count=GPU_WORKERS,
        maxsize=GPU_QUEUE_MAXSIZE,
        pipeline=pipeline,
    )
    await gpu_queue.start()
    app.state.pipeline = pipeline
    app.state.gpu_queue = gpu_queue
    app.state.started_at = time.time()
    logger.info("All models loaded and ready!")
    yield
    await app.state.gpu_queue.stop()
    logger.info("Shutting down AI server...")


app = FastAPI(
    title="Slacker-AI API",
    description="AI-powered expense tracking with OCR and ASR",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _request_id() -> str:
    return uuid.uuid4().hex


def _is_pipeline_ready() -> bool:
    return bool(getattr(app.state, "pipeline", None) and getattr(app.state, "gpu_queue", None))


async def _save_upload_to_temp(upload: UploadFile, max_bytes: int, default_suffix: str) -> str:
    content = await upload.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed is {max_bytes // MB}MB",
        )
    suffix = Path(upload.filename or "").suffix or default_suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        return tmp.name


@app.get("/health/live")
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    ready = _is_pipeline_ready()
    queue = getattr(app.state, "gpu_queue", None)
    return {
        "status": "ready" if ready else "not_ready",
        "models_loaded": bool(getattr(app.state, "pipeline", None)),
        "queue_running": bool(queue and queue._running),
        "queue_size": queue.queue.qsize() if queue else None,
        "queue_maxsize": queue.queue.maxsize if queue else None,
    }


@app.get("/health")
async def health_legacy():
    return await health_ready()


@app.post("/api/process/image")
async def process_image(file: UploadFile = File(...)):
    if not _is_pipeline_ready():
        raise HTTPException(status_code=503, detail="Models not loaded")

    request_id = _request_id()
    tmp_path = ""
    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        tmp_path = await _save_upload_to_temp(file, MAX_IMAGE_MB * MB, ".jpg")
        queue_result = await asyncio.wait_for(
            app.state.gpu_queue.submit(request_id, "image", {"path": tmp_path}),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        payload = queue_result["result"]
        payload["request_id"] = request_id
        payload["queue_wait_ms"] = queue_result["queue_wait_ms"]
        payload["latency_ms"] = queue_result["latency_ms"]
        return JSONResponse(content=payload)

    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Request timed out after {REQUEST_TIMEOUT_SEC}s",
        )
    except Exception as e:
        logger.error("Image processing error request_id=%s: %s", request_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Failed to delete temporary image file: %s", tmp_path)


@app.post("/api/process/audio")
async def process_audio(file: UploadFile = File(...)):
    if not _is_pipeline_ready():
        raise HTTPException(status_code=503, detail="Models not loaded")

    request_id = _request_id()
    tmp_path = ""
    try:
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be audio")

        tmp_path = await _save_upload_to_temp(file, MAX_AUDIO_MB * MB, ".wav")
        queue_result = await asyncio.wait_for(
            app.state.gpu_queue.submit(request_id, "audio", {"path": tmp_path}),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        payload = queue_result["result"]
        payload["request_id"] = request_id
        payload["queue_wait_ms"] = queue_result["queue_wait_ms"]
        payload["latency_ms"] = queue_result["latency_ms"]
        return JSONResponse(content=payload)

    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Request timed out after {REQUEST_TIMEOUT_SEC}s",
        )
    except Exception as e:
        logger.error("Audio processing error request_id=%s: %s", request_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Failed to delete temporary audio file: %s", tmp_path)


@app.post("/api/process/text")
async def process_text(text: str = Form(...)):
    if not _is_pipeline_ready():
        raise HTTPException(status_code=503, detail="Models not loaded")

    request_id = _request_id()
    try:
        queue_result = await asyncio.wait_for(
            app.state.gpu_queue.submit(request_id, "text", {"text": text}),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        payload = queue_result["result"]
        payload["request_id"] = request_id
        payload["queue_wait_ms"] = queue_result["queue_wait_ms"]
        payload["latency_ms"] = queue_result["latency_ms"]
        return JSONResponse(content=payload)

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Request timed out after {REQUEST_TIMEOUT_SEC}s",
        )
    except Exception as e:
        logger.error("Text processing error request_id=%s: %s", request_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def run_server():
    """Run the FastAPI server."""
    logger.info(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(
        "aicore.api_server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=SERVER_RELOAD,
        workers=UVICORN_WORKERS,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run_server()
