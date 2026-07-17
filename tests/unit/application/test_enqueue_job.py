"""
Unit tests for the EnqueueJob use case.
"""

from __future__ import annotations

from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.domain.value_objects.job_state import JobState
from tests.fakes.fake_job_repository import FakeJobRepository


def test_enqueue_job_creates_new_job() -> None:
    """
    EnqueueJob should create and persist a new job.
    """

    repository = FakeJobRepository()
    use_case = EnqueueJob(repository)

    payload = {
        "task": "send_email",
        "recipient": "alice@example.com",
    }

    job = use_case.execute(
        name="send_email",
        payload=payload,
        priority=5,
    )

    # Verify the repository contains the job
    assert repository.exists(job.id)

    saved_job = repository.get(job.id)

    # Verify the saved job
    assert saved_job is not None
    assert saved_job.id == job.id
    assert saved_job.name == "send_email"
    assert saved_job.payload == payload
    assert saved_job.priority == 5
    assert saved_job.state == JobState.PENDING
    assert saved_job.retry_count == 0
def test_enqueue_job_repository_count() -> None:
    """
    Repository should contain one job after enqueueing.
    """

    repository = FakeJobRepository()
    use_case = EnqueueJob(repository)

    assert repository.count() == 0

    use_case.execute(
        name="backup",
        payload={"path": "/tmp"},
    )

    assert repository.count() == 1