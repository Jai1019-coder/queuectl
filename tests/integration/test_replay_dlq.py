"""
Integration tests for replaying jobs from the Dead Letter Queue.

Workflow:

    Enqueue
        ↓
    Process
        ↓
    Fail
        ↓
    Retry ...
        ↓
    Move To DLQ
        ↓
    Replay
        ↓
    Process
        ↓
    Complete
"""

from datetime import UTC, datetime

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.get_status import GetStatus
from queuectl.application.use_cases.move_to_dlq import MoveToDlq
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.replay_dlq_job import ReplayDlqJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.repositories.in_memory_dlq_repository import (
    InMemoryDlqRepository,
)
from queuectl.infrastructure.repositories.in_memory_job_repository import (
    InMemoryJobRepository,
)


def test_replay_job_from_dead_letter_queue() -> None:
    """
    Verify that a dead-lettered job can be replayed and completed.
    """

    # ------------------------------------------------------------------
    # Arrange
    # ------------------------------------------------------------------

    job_repository = InMemoryJobRepository()
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
    replay_job = ReplayDlqJob(
        job_repository,
        dlq_repository,
    )
    complete_job = CompleteJob(job_repository)
    get_status = GetStatus(job_repository)

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    job = enqueue_job.execute(
        name="generate-report",
        priority=5,
    )

    # ------------------------------------------------------------------
    # Exhaust retries
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

        # Make immediately available for next retry.
        retried_job.available_at = datetime.now(UTC)
        job_repository.update(retried_job)

    # ------------------------------------------------------------------
    # Move to DLQ
    # ------------------------------------------------------------------

    dlq_entry = move_to_dlq.execute(
        job_id=job.id,
        reason="Retry limit exceeded",
    )

    assert dlq_entry is not None

    dead_job = get_status.execute(
        job_id=job.id,
    )

    assert dead_job.state == JobState.DEAD
    assert dead_job.retry_count == retry_policy.max_retries

    assert dlq_repository.count() == 1
    assert dlq_repository.exists(job.id)

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    replayed_job = replay_job.execute(
        job_id=job.id,
    )

    assert replayed_job.state == JobState.PENDING
    assert replayed_job.retry_count == 0
    assert replayed_job.worker_id is None
    assert replayed_job.error_message is None
    assert replayed_job.completed_at is None
    assert replayed_job.started_at is None

    # Should have been removed from DLQ.
    assert dlq_repository.count() == 0
    assert not dlq_repository.exists(job.id)

    # ------------------------------------------------------------------
    # Process again
    # ------------------------------------------------------------------

    processing_job = process_job.execute(
        worker_id="worker-replay",
    )

    assert processing_job is not None
    assert processing_job.state == JobState.PROCESSING
    assert processing_job.worker_id == "worker-replay"

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------

    completed_job = complete_job.execute(
        job_id=job.id,
    )

    assert completed_job.state == JobState.COMPLETED
    assert completed_job.is_completed()

    # ------------------------------------------------------------------
    # Final Verification
    # ------------------------------------------------------------------

    final_job = get_status.execute(
        job_id=job.id,
    )

    assert final_job.state == JobState.COMPLETED
    assert final_job.retry_count == 0
    assert final_job.completed_at is not None

    assert job_repository.count() == 1
    assert dlq_repository.count() == 0
