"""
Application use case for claiming the next available job.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.repositories.job_repository import JobRepository


class ProcessJob:
    """
    Claims the next available job for a worker.

    This use case is responsible for:

    - retrieving the next available job
    - assigning it to a worker
    - updating the repository
    """

    def __init__(self, repository: JobRepository) -> None:
        """
        Initialize the use case.

        Args:
            repository:
                Repository used to retrieve and persist jobs.
        """
        self._repository = repository

    def execute(
        self,
        *,
        worker_id: str,
    ) -> Job | None:
        """
        Claim the next available job.

        Args:
            worker_id:
                Identifier of the worker requesting work.

        Returns:
            The claimed job, or None if no job is available.
        """

        job = self._repository.next_available()

        if job is None:
            return None

        job.claim(worker_id)

        self._repository.update(job)

        return job