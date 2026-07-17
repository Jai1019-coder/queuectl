"""
Unit tests for FailJob use case.
"""

from __future__ import annotations

import pytest

from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState
from tests.fakes.fake_job_repository import FakeJobRepository


def test_fail_processing_job() -> None:
    """
    FailJob should mark a processing job as failed.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    fail = FailJob(repository)

    job = enqueue.execute(
        name="send_email",
        payload={"recipient": "alice@example.com"},
        priority=5,
    )

    process.execute(worker_id="worker-1")

    failed_job = fail.execute(
        job_id=job.id,
        error_message="SMTP server unavailable",
    )

    assert failed_job.state == JobState.FAILED
    assert failed_job.error_message == "SMTP server unavailable"

    saved_job = repository.get(job.id)

    assert saved_job is not None
    assert saved_job.state == JobState.FAILED
    assert saved_job.error_message == "SMTP server unavailable"


def test_fail_nonexistent_job_raises_error() -> None:
    """
    Failing a non-existent job should raise ValueError.
    """

    repository = FakeJobRepository()

    fail = FailJob(repository)

    invalid_job_id = JobId.generate()

    with pytest.raises(ValueError):
        fail.execute(
            job_id=invalid_job_id,
            error_message="Some error",
        )


def test_cannot_fail_pending_job() -> None:
    """
    A pending job cannot be failed.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    fail = FailJob(repository)

    job = enqueue.execute(
        name="backup",
    )

    with pytest.raises(ValueError):
        fail.execute(
            job_id=job.id,
            error_message="Unexpected failure",
        )


def test_failed_job_is_saved() -> None:
    """
    Repository should contain the updated failed job.
    """

    repository = FakeJobRepository()

    enqueue = EnqueueJob(repository)
    process = ProcessJob(repository)
    fail = FailJob(repository)

    job = enqueue.execute(
        name="cleanup",
    )

    process.execute(worker_id="worker-1")

    fail.execute(
        job_id=job.id,
        error_message="Disk full",
    )

    stored = repository.get(job.id)

    assert stored is not None
    assert stored.state == JobState.FAILED
    assert stored.error_message == "Disk full"