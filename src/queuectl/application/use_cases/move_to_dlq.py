"""
Application use case for moving a job to the Dead Letter Queue.
"""

from __future__ import annotations

from queuectl.domain.entities.dlq_entry import DlqEntry
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.dlq_repository import DlqRepository
from queuectl.repositories.job_repository import JobRepository


class MoveToDlq:
    """
    Moves a permanently failed job to the Dead Letter Queue.

    Responsibilities:
        - Retrieve the job.
        - Verify retry exhaustion.
        - Transition the job to DEAD.
        - Create a DLQ entry.
        - Persist both.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        dlq_repository: DlqRepository,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._dlq_repository = dlq_repository
        self._retry_policy = retry_policy or RetryPolicy()

    def execute(
        self,
        *,
        job_id: JobId,
        reason: str,
    ) -> DlqEntry:
        """
        Move a failed job into the Dead Letter Queue.

        Args:
            job_id:
                Identifier of the job.

            reason:
                Human-readable reason for moving the job to the DLQ.

        Returns:
            The created DlqEntry.

        Raises:
            ValueError:
                If the job does not exist.

            RuntimeError:
                If the retry limit has not yet been exhausted.

            Any exception raised by the domain entities is propagated.
        """

        job = self._job_repository.get(job_id)

        if job is None:
            raise ValueError(f"Job '{job_id}' does not exist.")

        if not self._retry_policy.is_exhausted(job.retry_count):
            raise RuntimeError("Job still has retry attempts remaining.")

        job.move_to_dead()

        self._job_repository.update(job)

        entry = DlqEntry.create(
            job_id=job.id,
            reason=reason,
            retry_count=job.retry_count,
            error_message=job.error_message or "",
        )

        self._dlq_repository.save(entry)

        return entry
