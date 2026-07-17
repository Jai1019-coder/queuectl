"""
Repository interface for Job aggregates.

Defines the persistence contract for Job entities.
Concrete implementations (SQLite, PostgreSQL, etc.)
must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

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