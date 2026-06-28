import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackgroundJobSubmission:
    job_id: UUID
    queue_name: str
    backend_name: str


class BackgroundJobBackend:
    queue_name: str = "default"
    backend_name: str = "abstract"

    def submit(self, job_id: UUID, task: Callable[[], None]) -> BackgroundJobSubmission:
        raise NotImplementedError


@dataclass(frozen=True)
class InlineBackgroundJobBackend(BackgroundJobBackend):
    queue_name: str = "rag-ingestion"
    backend_name: str = "inline-local"

    def submit(self, job_id: UUID, task: Callable[[], None]) -> BackgroundJobSubmission:
        task()
        return BackgroundJobSubmission(
            job_id=job_id,
            queue_name=self.queue_name,
            backend_name=self.backend_name,
        )


@dataclass(frozen=True)
class ThreadedBackgroundJobBackend(BackgroundJobBackend):
    queue_name: str = "rag-ingestion"
    backend_name: str = "threaded-worker"

    def submit(self, job_id: UUID, task: Callable[[], None]) -> BackgroundJobSubmission:
        def worker_loop() -> None:
            max_retries = 3
            backoff = 1.0
            for attempt in range(max_retries + 1):
                try:
                    task()
                    return
                except Exception as exc:
                    if attempt == max_retries:
                        logger.error(
                            f"Job {job_id} failed after {max_retries} retries: {exc}",
                            exc_info=True,
                        )
                        return
                    logger.warning(
                        f"Job {job_id} failed on attempt {attempt + 1}. Retrying in {backoff}s... Error: {exc}"
                    )
                    time.sleep(backoff)
                    backoff *= 2.0

        thread = threading.Thread(target=worker_loop, name=f"job-{job_id}", daemon=True)
        thread.start()
        return BackgroundJobSubmission(
            job_id=job_id,
            queue_name=self.queue_name,
            backend_name=self.backend_name,
        )
