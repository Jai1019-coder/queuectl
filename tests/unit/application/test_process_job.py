"""
Unit tests for ProcessJob use case.
"""

from __future__ import annotations

from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.domain.value_objects.job_state import JobState
from tests.fakes.fake_job_repository import FakeJobRepository


def test_process_job_claims_next_available_job() -> None:
    """
    ProcessJob should claim the next available job.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)

    enqueue.execute(
        name="send_email",
        payload={"recipient": "alice@example.com"},
        priority=5,
    )

    job = process.execute(worker_id="worker-1")

    assert job is not None
    assert job.worker_id == "worker-1"
    assert job.state == JobState.PROCESSING

    saved_job = repository.get(job.id)

    assert saved_job is not None
    assert saved_job.worker_id == "worker-1"
    assert saved_job.state == JobState.PROCESSING

def test_process_job_returns_none_when_queue_is_empty() -> None:
    """
    ProcessJob should return None when no jobs exist.
    """

    repository = FakeJobRepository()

    process = ProcessJob(repository)

    job = process.execute(worker_id="worker-1")

    assert job is None

def test_process_job_claims_highest_priority_job() -> None:
    """
    Highest priority job should be claimed first.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)

    enqueue.execute(
        name="low",
        priority=1,
    )

    enqueue.execute(
        name="high",
        priority=10,
    )

    job = process.execute(worker_id="worker-1")

    assert job is not None
    assert job.name == "high"
    assert job.priority == 10

def test_claimed_job_is_no_longer_available() -> None:
    """
    A claimed job should not be returned again.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)

    enqueue.execute(
        name="job",
    )

    first = process.execute(worker_id="worker-1")
    second = process.execute(worker_id="worker-2")

    assert first is not None
    assert second is None