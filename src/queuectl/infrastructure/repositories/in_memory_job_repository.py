"""
In-memory implementation of JobRepository.

Primarily intended for testing and local development.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState
from queuectl.repositories.job_repository import JobRepository


class InMemoryJobRepository(JobRepository):
    """
    In-memory implementation of the JobRepository interface.

    Jobs are stored in a dictionary keyed by JobId.
    """

    def __init__(self) -> None:
        """
        Initialize an empty repository.
        """
        self._jobs: dict[JobId, Job] = {}

    def save(self, job: Job) -> None:
        """
        Persist a new job.

        Raises:
            ValueError:
                If a job with the same ID already exists.
        """
        if job.id in self._jobs:
            raise ValueError(f"Job {job.id} already exists.")

        self._jobs[job.id] = job

    def get(self, job_id: JobId) -> Job | None:
        """
        Retrieve a job by its identifier.
        """
        return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        """
        Persist changes to an existing job.

        Raises:
            ValueError:
                If the job does not exist.
        """
        if job.id not in self._jobs:
            raise ValueError(f"Job {job.id} does not exist.")

        self._jobs[job.id] = job

    def delete(self, job_id: JobId) -> None:
        """
        Delete a job.

        Does nothing if the job does not exist.
        """
        self._jobs.pop(job_id, None)

    def exists(self, job_id: JobId) -> bool:
        """
        Determine whether a job exists.
        """
        return job_id in self._jobs

    def list(
        self,
        *,
        state: JobState | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Job]:
        """
        List jobs.

        Jobs are returned ordered by creation time.
        """

        jobs = sorted(
            self._jobs.values(),
            key=lambda job: job.created_at,
        )

        if state is not None:
            jobs = [job for job in jobs if job.state is state]

        if offset > 0:
            jobs = jobs[offset:]

        if limit is not None:
            jobs = jobs[:limit]

        return jobs

    def next_available(self) -> Job | None:
        """
        Return the highest-priority schedulable job.

        Ordering:

        1. Higher priority first.
        2. Earlier creation time first.
        """

        candidates = [
            job
            for job in self._jobs.values()
            if job.can_be_claimed()
        ]

        if not candidates:
            return None

        candidates.sort(
            key=lambda job: (
                -job.priority,
                job.created_at,
            )
        )

        return candidates[0]

    def count(
        self,
        *,
        state: JobState | None = None,
    ) -> int:
        """
        Count jobs.

        Optionally filter by state.
        """

        if state is None:
            return len(self._jobs)

        return sum(
            1
            for job in self._jobs.values()
            if job.state is state
        )

    def clear(self) -> None:
        """
        Remove all jobs.

        Primarily intended for testing.
        """
        self._jobs.clear()

    def __len__(self) -> int:
        """
        Return the number of stored jobs.
        """
        return len(self._jobs)

    def __contains__(self, job_id: JobId) -> bool:
        """
        Determine whether the repository contains a job.
        """
        return job_id in self._jobs

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation.
        """
        return (
            f"{self.__class__.__name__}"
            f"(jobs={len(self._jobs)})"
        )