"""
Application use case for enqueuing a new job.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.repositories.job_repository import JobRepository


class EnqueueJob:
    """
    Creates and persists a new job.
    """

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        name: str,
        payload: dict | None = None,
        priority: int = 0,
    ) -> Job:
        """
        Create and enqueue a new job.
        """

        job = Job.create(
            name=name,
            payload=payload,
            priority=priority,
        )

        self._repository.save(job)

        return job