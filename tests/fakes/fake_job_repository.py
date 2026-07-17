"""
In-memory implementation of JobRepository for unit testing.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState
from queuectl.repositories.job_repository import JobRepository


class FakeJobRepository(JobRepository):
    """
    In-memory implementation of JobRepository.

    Stores jobs in a Python dictionary and is intended
    exclusively for unit testing.
    """

    def __init__(self) -> None:
        self._jobs: dict[JobId, Job] = {}

    def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: JobId) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        self._jobs[job.id] = job

    def delete(self, job_id: JobId) -> None:
        self._jobs.pop(job_id, None)

    def exists(self, job_id: JobId) -> bool:
        return job_id in self._jobs

    def list(
        self,
        *,
        state: JobState | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Job]:
        jobs = list(self._jobs.values())

        if state is not None:
            jobs = [job for job in jobs if job.state == state]

        jobs = jobs[offset:]

        if limit is not None:
            jobs = jobs[:limit]

        return jobs

    def next_available(self) -> Job | None:
        available_jobs = [
            job
            for job in self._jobs.values()
            if job.state == JobState.PENDING
        ]

        if not available_jobs:
            return None

        return max(
            available_jobs,
            key=lambda job: (job.priority, job.created_at),
        )

    def count(
        self,
        *,
        state: JobState | None = None,
    ) -> int:
        if state is None:
            return len(self._jobs)

        return sum(
            1
            for job in self._jobs.values()
            if job.state == state
        )

    def clear(self) -> None:
        self._jobs.clear()