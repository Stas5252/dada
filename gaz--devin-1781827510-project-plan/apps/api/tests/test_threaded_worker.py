import time
from uuid import uuid4

from app.jobs import ThreadedBackgroundJobBackend


def test_threaded_backend_success() -> None:
    backend = ThreadedBackgroundJobBackend()
    job_id = uuid4()
    called = []

    def task():
        called.append(True)

    submission = backend.submit(job_id, task)
    assert submission.job_id == job_id
    assert submission.backend_name == "threaded-worker"

    # Wait for daemon thread to execute
    for _ in range(50):
        if called:
            break
        time.sleep(0.01)

    assert called == [True]


def test_threaded_backend_retries_and_fails(monkeypatch) -> None:
    backend = ThreadedBackgroundJobBackend()
    job_id = uuid4()
    attempts = []
    sleeps = []

    class MockTime:
        @staticmethod
        def sleep(secs):
            sleeps.append(secs)

    monkeypatch.setattr("app.jobs.time", MockTime)

    def failing_task():
        attempts.append(True)
        raise ValueError("transient failure")

    backend.submit(job_id, failing_task)

    # Wait for the worker thread to finish executing (max 4 attempts)
    for _ in range(100):
        if len(attempts) >= 4:
            break
        time.sleep(0.01)

    assert len(attempts) == 4
    assert sleeps == [1.0, 2.0, 4.0]
