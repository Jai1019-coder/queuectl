"""
Application use case for completing a job.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.job_repository import JobRepository


class CompleteJob:
    """
    Marks a processing job as completed.

    Responsibilities:
        - Retrieve the job.
        - Mark it as completed.
        - Persist the updated job.
    """

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        job_id: JobId,
    ) -> Job:
        """
        Complete a processing job.

        Args:
            job_id:
                Identifier of the job to complete.

        Returns:
            The completed job.

        Raises:
            ValueError:
                If the job does not exist.
                Any domain exception raised by Job.mark_completed()
                is intentionally propagated.
        """

        job = self._repository.get(job_id)

        if job is None:
            raise ValueError(f"Job '{job_id}' does not exist.")

        job.mark_completed()

        self._repository.update(job)

        return job
