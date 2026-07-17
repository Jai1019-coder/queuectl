"""
Unit tests for CompleteJob use case.
"""

from __future__ import annotations

import pytest

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.domain.value_objects.job_state import JobState
from tests.fakes.fake_job_repository import FakeJobRepository


def test_complete_processing_job() -> None:
    """
    CompleteJob should mark a processing job as completed.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    complete = CompleteJob(repository)

    job = enqueue.execute(
        name="send_email",
        payload={"recipient": "alice@example.com"},
        priority=5,
    )

    process.execute(worker_id="worker-1")

    completed_job = complete.execute(job_id=job.id)

    assert completed_job.state == JobState.COMPLETED
    assert completed_job.completed_at is not None

    saved_job = repository.get(job.id)

    assert saved_job is not None
    assert saved_job.state == JobState.COMPLETED
    assert saved_job.completed_at is not None

def test_complete_nonexistent_job_raises_error() -> None:
    """
    Completing a non-existent job should raise ValueError.
    """

    repository = FakeJobRepository()

    complete = CompleteJob(repository)

    with pytest.raises(ValueError):
        complete.execute(job_id="invalid-job-id")

def test_cannot_complete_pending_job() -> None:
    """
    A pending job cannot be completed.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    complete = CompleteJob(repository)

    job = enqueue.execute(
        name="backup",
    )

    with pytest.raises(ValueError):
        complete.execute(job_id=job.id)

def test_completed_job_is_saved() -> None:
    """
    Repository should contain the updated completed job.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    complete = CompleteJob(repository)

    job = enqueue.execute(
        name="cleanup",
    )

    process.execute(worker_id="worker-1")

    complete.execute(job_id=job.id)

    stored = repository.get(job.id)

    assert stored is not None
    assert stored.state == JobState.COMPLETED