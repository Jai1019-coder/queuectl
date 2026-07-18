"""
Application use case for retrieving the status of a job.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.job_repository import JobRepository


class GetStatus:
    """
    Retrieves the current status of a job.

    Responsibilities:
        - Retrieve the job by its identifier.
        - Return the job.

    This use case performs no state changes.
    """

    def __init__(
        self,
        repository: JobRepository,
    ) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        job_id: JobId,
    ) -> Job:
        """
        Retrieve a job.

        Args:
            job_id:
                Identifier of the job.

        Returns:
            The requested job.

        Raises:
            ValueError:
                If the job does not exist.
        """

        job = self._repository.get(job_id)

        if job is None:
            raise ValueError(f"Job '{job_id}' does not exist.")

        return job
