"""
Unit tests for RetryJob use case.
"""

from __future__ import annotations

import pytest

from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState
from tests.fakes.fake_job_repository import FakeJobRepository


def test_retry_failed_job() -> None:
    """
    RetryJob should reschedule a failed job.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    fail = FailJob(repository)
    retry = RetryJob(repository)

    job = enqueue.execute(
        name="send_email",
        payload={"recipient": "alice@example.com"},
        priority=5,
    )

    process.execute(worker_id="worker-1")

    fail.execute(
        job_id=job.id,
        error_message="SMTP unavailable",
    )

    previous_available_at = job.available_at

    retried_job = retry.execute(job_id=job.id)

    assert retried_job is not None
    assert retried_job.state == JobState.PENDING
    assert retried_job.retry_count == 1
    assert retried_job.available_at > previous_available_at

    stored = repository.get(job.id)

    assert stored is not None
    assert stored.state == JobState.PENDING
    assert stored.retry_count == 1


def test_retry_nonexistent_job_raises_error() -> None:
    """
    Retrying a non-existent job should raise ValueError.
    """

    repository = FakeJobRepository()

    retry = RetryJob(repository)

    invalid_job_id = JobId.generate()

    with pytest.raises(ValueError):
        retry.execute(job_id=invalid_job_id)


def test_retry_limit_reached_returns_none() -> None:
    """
    RetryJob should return None when retries are exhausted.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    fail = FailJob(repository)

    retry_policy = RetryPolicy(max_retries=1)
    retry = RetryJob(repository, retry_policy)

    job = enqueue.execute(name="cleanup")

    process.execute(worker_id="worker-1")

    fail.execute(
        job_id=job.id,
        error_message="Disk full",
    )

    # Simulate that the retry limit has already been reached.
    job.retry_count = 1
    repository.update(job)

    assert retry.execute(job_id=job.id) is None


def test_retry_updates_repository() -> None:
    """
    Repository should contain the updated retried job.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    fail = FailJob(repository)
    retry = RetryJob(repository)

    job = enqueue.execute(name="backup")

    process.execute(worker_id="worker-1")

    fail.execute(
        job_id=job.id,
        error_message="Connection timeout",
    )

    retry.execute(job_id=job.id)

    stored = repository.get(job.id)

    assert stored is not None
    assert stored.state == JobState.PENDING
    assert stored.retry_count == 1


def test_retry_increments_retry_count() -> None:
    """
    Retry count should increase by one.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    fail = FailJob(repository)
    retry = RetryJob(repository)

    job = enqueue.execute(name="sync")

    process.execute(worker_id="worker-1")

    fail.execute(
        job_id=job.id,
        error_message="Network failure",
    )

    assert job.retry_count == 0

    retry.execute(job_id=job.id)

    assert job.retry_count == 1
