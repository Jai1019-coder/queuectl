"""
Application use case for marking a job as failed.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.job_repository import JobRepository


class FailJob:
    """
    Marks a processing job as failed.

    Responsibilities:
        - Retrieve the job.
        - Mark it as failed.
        - Persist the updated job.
    """

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        job_id: JobId,
        error_message: str,
    ) -> Job:
        """
        Mark a job as failed.

        Args:
            job_id:
                Identifier of the job.

            error_message:
                Description of the failure.

        Returns:
            The failed job.

        Raises:
            ValueError:
                If the job does not exist.

            Any exception raised by Job.mark_failed()
            is intentionally propagated.
        """

        job = self._repository.get(job_id)

        if job is None:
            raise ValueError(f"Job '{job_id}' does not exist.")

        job.mark_failed(error_message)

        self._repository.update(job)

        return job
