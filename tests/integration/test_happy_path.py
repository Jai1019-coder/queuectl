"""
Integration tests for the basic QueueCTL workflow.

Workflow:

    Enqueue
        ↓
    Process
        ↓
    Complete
"""

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.get_status import GetStatus
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.repositories.in_memory_job_repository import (
    InMemoryJobRepository,
)


def test_enqueue_process_complete_happy_path() -> None:
    """
    Verify that a job successfully flows through:

        PENDING
            ↓
        PROCESSING
            ↓
        COMPLETED
    """

    # ------------------------------------------------------------------
    # Arrange
    # ------------------------------------------------------------------

    repository = InMemoryJobRepository()

    enqueue_job = EnqueueJob(repository)
    process_job = ProcessJob(repository)
    complete_job = CompleteJob(repository)
    get_status = GetStatus(repository)

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    job = enqueue_job.execute(
        name="send-email",
        payload={
            "to": "alice@example.com",
            "subject": "Welcome",
        },
        priority=10,
    )

    assert repository.count() == 1

    stored_job = repository.get(job.id)

    assert stored_job is not None
    assert stored_job.state == JobState.PENDING
    assert stored_job.worker_id is None

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------

    claimed_job = process_job.execute(
        worker_id="worker-1",
    )

    assert claimed_job is not None
    assert claimed_job.id == job.id
    assert claimed_job.state == JobState.PROCESSING
    assert claimed_job.worker_id == "worker-1"

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------

    completed_job = complete_job.execute(
        job_id=job.id,
    )

    assert completed_job.state == JobState.COMPLETED

    # ------------------------------------------------------------------
    # Verify persisted state
    # ------------------------------------------------------------------

    final_job = get_status.execute(
        job_id=job.id,
    )

    assert final_job.id == job.id
    assert final_job.state == JobState.COMPLETED
    assert final_job.worker_id == "worker-1"

    assert repository.count() == 1
