"""
Repository interface for Job aggregates.

Defines the persistence contract for Job entities.
Concrete implementations (SQLite, PostgreSQL, etc.)
must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState


class JobRepository(ABC):
    """
    Abstract repository for Job aggregate roots.
    """

    @abstractmethod
    def save(self, job: Job) -> None:
        """
        Persist a new job.

        Args:
            job: Job entity to persist.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: JobId) -> Job | None:
        """
        Retrieve a job by its unique identifier.

        Args:
            job_id: Job identifier.

        Returns:
            The matching Job if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, job: Job) -> None:
        """
        Persist changes made to an existing job.

        Args:
            job: Updated Job entity.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, job_id: JobId) -> None:
        """
        Delete a job.

        Args:
            job_id: Identifier of the job.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, job_id: JobId) -> bool:
        """
        Determine whether a job exists.

        Args:
            job_id: Job identifier.

        Returns:
            True if the job exists, otherwise False.
        """
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        *,
        state: JobState | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Job]:
        """
        List jobs.

        Args:
            state:
                Optional state filter.

            limit:
                Maximum number of jobs to return.

            offset:
                Pagination offset.

        Returns:
            List of matching jobs.
        """
        raise NotImplementedError

    @abstractmethod
    def next_available(self) -> Job | None:
        """
        Retrieve the next schedulable job.

        The repository implementation should return the
        highest-priority queued job that is ready to run.

        Returns:
            Job if available, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def claim_next(
        self,
        worker_id: str,
        *,
        now: datetime | None = None,
    ) -> Job | None:
        """
        Atomically claim the next available job for a worker.

        Implementations MUST guarantee that when multiple callers
        (threads, processes, or workers) invoke this method
        concurrently, at most one caller receives any given job.
        This is the only safe way to claim work; ``next_available``
        is a non-atomic preview and must never be used to drive
        job execution.

        Args:
            worker_id:
                Identifier of the worker claiming the job.

            now:
                Reference timestamp used to evaluate availability
                and to stamp the claim. Defaults to the current
                UTC time.

        Returns:
            The claimed job (already transitioned to ``PROCESSING``
            and persisted), or None if no job is currently available.
        """
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        *,
        state: JobState | None = None,
    ) -> int:
        """
        Count jobs.

        Args:
            state:
                Optional state filter.

        Returns:
            Number of matching jobs.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all jobs.

        Primarily intended for testing.
        """
        raise NotImplementedError
