"""
Integration tests for the Dead Letter Queue workflow.

Workflow:

    Enqueue
        ↓
    (Process → Fail → Retry)* until retries exhausted
        ↓
    Move To DLQ
"""

from datetime import UTC, datetime

from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.get_status import GetStatus
from queuectl.application.use_cases.move_to_dlq import MoveToDlq
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import initialize_database
from queuectl.infrastructure.repositories.in_memory_dlq_repository import (
    InMemoryDlqRepository,
)
from queuectl.infrastructure.repositories.sqlite_job_repository import (
    SQLiteJobRepository,
)

connection = SQLiteConnection(":memory:")

initialize_database(connection)


def test_move_job_to_dead_letter_queue() -> None:
    """
    Verify that a job is moved to the DLQ once all retries are exhausted.
    """

    # ------------------------------------------------------------------
    # Arrange
    # ------------------------------------------------------------------

    job_repository = SQLiteJobRepository(connection)
    dlq_repository = InMemoryDlqRepository()

    retry_policy = RetryPolicy(max_retries=3)

    enqueue_job = EnqueueJob(job_repository)
    process_job = ProcessJob(job_repository)
    fail_job = FailJob(job_repository)
    retry_job = RetryJob(job_repository, retry_policy)
    move_to_dlq = MoveToDlq(
        job_repository,
        dlq_repository,
        retry_policy,
    )
    get_status = GetStatus(job_repository)

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    job = enqueue_job.execute(
        name="generate-report",
        priority=5,
    )

    # ------------------------------------------------------------------
    # Keep retrying until RetryPolicy refuses another retry.
    # ------------------------------------------------------------------

    while True:

        processing_job = process_job.execute(
            worker_id="worker-1",
        )

        assert processing_job is not None
        assert processing_job.state == JobState.PROCESSING

        failed_job = fail_job.execute(
            job_id=job.id,
            error_message="Processing failed",
        )

        assert failed_job.state == JobState.FAILED

        retried_job = retry_job.execute(
            job_id=job.id,
        )

        if retried_job is None:
            break

        # Make the job immediately available again.
        retried_job.available_at = datetime.now(UTC)
        job_repository.update(retried_job)

    # ------------------------------------------------------------------
    # Move to DLQ
    # ------------------------------------------------------------------

    entry = move_to_dlq.execute(
        job_id=job.id,
        reason="Retry limit exceeded",
    )

    # ------------------------------------------------------------------
    # Verify Job
    # ------------------------------------------------------------------

    dead_job = get_status.execute(
        job_id=job.id,
    )

    assert dead_job.state == JobState.DEAD
    assert dead_job.is_dead()

    assert dead_job.retry_count == retry_policy.max_retries

    # ------------------------------------------------------------------
    # Verify DLQ
    # ------------------------------------------------------------------

    assert dlq_repository.count() == 1

    stored_entry = dlq_repository.get(job.id)

    assert stored_entry is not None
    assert stored_entry.job_id == job.id
    assert stored_entry.reason == "Retry limit exceeded"
    assert stored_entry.retry_count == retry_policy.max_retries

    assert entry == stored_entry
