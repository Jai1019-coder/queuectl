"""
Application use case for replaying a job from the Dead Letter Queue.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.dlq_repository import DlqRepository
from queuectl.repositories.job_repository import JobRepository


class ReplayDlqJob:
    """
    Replays a job from the Dead Letter Queue.

    Responsibilities:
        - Retrieve the DLQ entry.
        - Retrieve the associated job.
        - Reset the job.
        - Persist the updated job.
        - Remove the DLQ entry.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        dlq_repository: DlqRepository,
    ) -> None:
        self._job_repository = job_repository
        self._dlq_repository = dlq_repository

    def execute(
        self,
        *,
        job_id: JobId,
    ) -> Job:
        """
        Replay a job from the Dead Letter Queue.

        Args:
            job_id:
                Identifier of the job.

        Returns:
            The reset job.

        Raises:
            ValueError:
                If the job or DLQ entry does not exist.

            Any exception raised by the domain entity is propagated.
        """

        dlq_entry = self._dlq_repository.get(job_id)

        if dlq_entry is None:
            raise ValueError(f"DLQ entry for job '{job_id}' does not exist.")

        job = self._job_repository.get(job_id)

        if job is None:
            raise ValueError(f"Job '{job_id}' does not exist.")

        job.reset()

        self._job_repository.update(job)

        self._dlq_repository.delete(job_id)

        return job
