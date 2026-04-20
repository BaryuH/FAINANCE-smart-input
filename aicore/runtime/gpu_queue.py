import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict


logger = logging.getLogger(__name__)


@dataclass
class QueueJob:
    request_id: str
    task_type: str
    payload: Dict[str, Any]
    enqueued_at: float
    future: asyncio.Future


class GpuTaskQueue:
    """Bounded async queue that runs model tasks via worker pool."""

    def __init__(
        self,
        *,
        worker_count: int,
        maxsize: int,
        pipeline: Any,
    ) -> None:
        self.pipeline = pipeline
        self.queue: asyncio.Queue[QueueJob] = asyncio.Queue(maxsize=maxsize)
        self.worker_count = max(1, worker_count)
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for idx in range(self.worker_count):
            self._workers.append(asyncio.create_task(self._worker_loop(idx)))
        logger.info(
            "GPU queue started: workers=%s maxsize=%s",
            self.worker_count,
            self.queue.maxsize,
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("GPU queue stopped")

    async def submit(self, request_id: str, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._running:
            raise RuntimeError("GPU queue is not running")

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        job = QueueJob(
            request_id=request_id,
            task_type=task_type,
            payload=payload,
            enqueued_at=time.perf_counter(),
            future=future,
        )
        await self.queue.put(job)
        return await future

    async def _worker_loop(self, worker_index: int) -> None:
        while True:
            job = await self.queue.get()
            started_at = time.perf_counter()
            queue_wait_ms = int((started_at - job.enqueued_at) * 1000)
            try:
                result = await asyncio.to_thread(self._run_task, job.task_type, job.payload)
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                if not job.future.done():
                    job.future.set_result(
                        {
                            "request_id": job.request_id,
                            "queue_wait_ms": queue_wait_ms,
                            "latency_ms": latency_ms,
                            "result": result,
                        }
                    )
            except Exception as exc:
                logger.exception(
                    "Worker %s failed request_id=%s type=%s",
                    worker_index,
                    job.request_id,
                    job.task_type,
                )
                if not job.future.done():
                    job.future.set_exception(exc)
            finally:
                self.queue.task_done()

    def _run_task(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        handlers: dict[str, Callable[..., Dict[str, Any]]] = {
            "image": self.pipeline.process_image,
            "audio": self.pipeline.process_audio,
            "text": self.pipeline.process_text,
        }
        if task_type not in handlers:
            raise ValueError(f"Unsupported task type: {task_type}")
        if task_type == "text":
            return handlers[task_type](payload["text"])
        return handlers[task_type](payload["path"])
