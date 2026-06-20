from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID


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
