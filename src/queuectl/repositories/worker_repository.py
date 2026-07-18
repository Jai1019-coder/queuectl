"""
Repository interface for Worker aggregates.

Defines the persistence contract for Worker entities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.worker_status import WorkerStatus


class WorkerRepository(ABC):
    """
    Abstract repository for Worker aggregate roots.
    """

    @abstractmethod
    def save(self, worker: Worker) -> None:
        """
        Persist a new worker.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, worker_id: str) -> Worker | None:
        """
        Retrieve a worker by its identifier.
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, worker: Worker) -> None:
        """
        Persist changes to an existing worker.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, worker_id: str) -> None:
        """
        Remove a worker.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, worker_id: str) -> bool:
        """
        Check whether a worker exists.
        """
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        *,
        status: WorkerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Worker]:
        """
        List workers.

        Optionally filter by status.
        """
        raise NotImplementedError

    @abstractmethod
    def list_available(self) -> list[Worker]:
        """
        Return workers currently available to execute jobs.
        """
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        *,
        status: WorkerStatus | None = None,
    ) -> int:
        """
        Count workers.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all workers.

        Intended primarily for testing.
        """
        raise NotImplementedError
