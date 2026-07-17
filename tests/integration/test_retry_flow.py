"""
Integration tests for the retry workflow.

Workflow:

    Enqueue
        ↓
    Process
        ↓
    Fail
        ↓
    Retry
        ↓
    Process
        ↓
    Complete
"""

from datetime import datetime, timezone

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.get_status import GetStatus
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.repositories.in_memory_job_repository import (
    InMemoryJobRepository,
)


def test_retry_failed_job_successfully() -> None:
    """
    Verify that a failed job can be retried and completed.
    """

    # -------------------------------------------------------------
    # Arrange
    # -------------------------------------------------------------

    repository = InMemoryJobRepository()

    enqueue_job = EnqueueJob(repository)
    process_job = ProcessJob(repository)
    fail_job = FailJob(repository)
    retry_job = RetryJob(repository)
    complete_job = CompleteJob(repository)
    get_status = GetStatus(repository)

    # -------------------------------------------------------------
    # Enqueue
    # -------------------------------------------------------------

    job = enqueue_job.execute(
        name="generate-report",
        payload={"month": "June"},
        priority=5,
    )

    # -------------------------------------------------------------
    # Process
    # -------------------------------------------------------------

    processing_job = process_job.execute(
        worker_id="worker-1",
    )

    assert processing_job is not None
    assert processing_job.state == JobState.PROCESSING

    # -------------------------------------------------------------
    # Fail
    # -------------------------------------------------------------

    failed_job = fail_job.execute(
        job_id=job.id,
        error_message="Database timeout",
    )

    assert failed_job.state == JobState.FAILED
    assert failed_job.retry_count == 0
    assert failed_job.error_message == "Database timeout"

    # -------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------

    retried_job = retry_job.execute(
        job_id=job.id,
    )

    assert retried_job is not None
    assert retried_job.retry_count == 1

    assert retried_job.state == JobState.PENDING

    assert retried_job.available_at > datetime.now(timezone.utc)

    # -------------------------------------------------------------
    # Simulate retry delay elapsed
    # -------------------------------------------------------------

    retried_job.available_at = datetime.now(timezone.utc)

    repository.update(retried_job)

    # -------------------------------------------------------------
    # Process Again
    # -------------------------------------------------------------

    processing_job = process_job.execute(
        worker_id="worker-2",
    )

    assert processing_job is not None
    assert processing_job.state == JobState.PROCESSING
    assert processing_job.worker_id == "worker-2"

    # -------------------------------------------------------------
    # Complete
    # -------------------------------------------------------------

    completed_job = complete_job.execute(
        job_id=job.id,
    )

    assert completed_job.state == JobState.COMPLETED

    # -------------------------------------------------------------
    # Verify persisted state
    # -------------------------------------------------------------

    final_job = get_status.execute(
        job_id=job.id,
    )

    assert final_job.state == JobState.COMPLETED
    assert final_job.retry_count == 1
    assert final_job.worker_id == "worker-2"

    assert repository.count() == 1