import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackgroundJobSubmission:
    job_id: UUID
    queue_name: str
    backend_name: str


class BackgroundJobBackend:
    queue_name: str = "default"
    backend_name: str = "abstract"

    def submit(self, job_name: str, job_id: UUID, *args: Any, **kwargs: Any) -> BackgroundJobSubmission:
        raise NotImplementedError


@dataclass(frozen=True)
class InlineBackgroundJobBackend(BackgroundJobBackend):
    queue_name: str = "rag-ingestion"
    backend_name: str = "inline-local"

    def submit(self, job_name: str, job_id: UUID, *args: Any, **kwargs: Any) -> BackgroundJobSubmission:
        from app.worker import RUN_KNOWLEDGE_INGESTION, RUN_TESTBED_SYNC, RUN_QA_EVAL, RUN_WEEKLY_REPORT
        
        store = kwargs.pop('_store', None)
        ctx = {"store": store}
        
        if job_name == "run_knowledge_ingestion":
            RUN_KNOWLEDGE_INGESTION(ctx, job_id, *args, **kwargs)
        elif job_name == "run_testbed_sync":
            RUN_TESTBED_SYNC(ctx, job_id, *args, **kwargs)
        elif job_name == "run_qa_eval":
            import asyncio
            try:
                asyncio.get_running_loop().create_task(RUN_QA_EVAL(ctx, job_id, *args, **kwargs))
            except RuntimeError:
                asyncio.run(RUN_QA_EVAL(ctx, job_id, *args, **kwargs))
        elif job_name == "run_weekly_report":
            import asyncio
            try:
                asyncio.get_running_loop().create_task(RUN_WEEKLY_REPORT(ctx, job_id, *args, **kwargs))
            except RuntimeError:
                asyncio.run(RUN_WEEKLY_REPORT(ctx, job_id, *args, **kwargs))
        else:
            logger.warning(f"Inline job backend unknown job: {job_name}")
            
        return BackgroundJobSubmission(
            job_id=job_id,
            queue_name=self.queue_name,
            backend_name=self.backend_name,
        )


@dataclass(frozen=True)
class ArqBackgroundJobBackend(BackgroundJobBackend):
    redis_pool: ArqRedis
    queue_name: str = "default"
    backend_name: str = "arq-redis"

    def submit(self, job_name: str, job_id: UUID, *args: Any, **kwargs: Any) -> BackgroundJobSubmission:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.redis_pool.enqueue_job(job_name, job_id, *args, _job_id=str(job_id), **kwargs))
        except RuntimeError:
            # If no running loop, we run it synchronously (e.g. from tests or scripts)
            asyncio.run(self.redis_pool.enqueue_job(job_name, job_id, *args, _job_id=str(job_id), **kwargs))
            
        return BackgroundJobSubmission(
            job_id=job_id,
            queue_name=self.queue_name,
            backend_name=self.backend_name,
        )
