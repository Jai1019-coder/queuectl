"""
In-memory implementation of WorkerRepository.

Primarily intended for testing and local development.
"""

from __future__ import annotations

from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.worker_status import WorkerStatus
from queuectl.repositories.worker_repository import WorkerRepository


class InMemoryWorkerRepository(WorkerRepository):
    """
    In-memory implementation of the WorkerRepository interface.

    Workers are stored in a dictionary keyed by worker ID.
    """

    def __init__(self) -> None:
        """
        Initialize an empty repository.
        """
        self._workers: dict[str, Worker] = {}

    def save(self, worker: Worker) -> None:
        """
        Persist a new worker.

        Raises:
            ValueError:
                If a worker with the same ID already exists.
        """
        if worker.id in self._workers:
            raise ValueError(f"Worker '{worker.id}' already exists.")

        self._workers[worker.id] = worker

    def get(self, worker_id: str) -> Worker | None:
        """
        Retrieve a worker by its identifier.
        """
        return self._workers.get(worker_id)

    def update(self, worker: Worker) -> None:
        """
        Persist changes made to an existing worker.

        Raises:
            ValueError:
                If the worker does not exist.
        """
        if worker.id not in self._workers:
            raise ValueError(f"Worker '{worker.id}' does not exist.")

        self._workers[worker.id] = worker

    def delete(self, worker_id: str) -> None:
        """
        Remove a worker.

        Does nothing if the worker does not exist.
        """
        self._workers.pop(worker_id, None)

    def exists(self, worker_id: str) -> bool:
        """
        Determine whether a worker exists.
        """
        return worker_id in self._workers

    def list(
        self,
        *,
        status: WorkerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Worker]:
        """
        List workers.

        Workers are ordered by registration time.
        """

        workers = sorted(
            self._workers.values(),
            key=lambda worker: worker.started_at,
        )

        if status is not None:
            workers = [worker for worker in workers if worker.status is status]

        if offset > 0:
            workers = workers[offset:]

        if limit is not None:
            workers = workers[:limit]

        return workers

    def list_available(self) -> list[Worker]:
        """
        Return workers currently available to execute jobs.
        """

        workers = [worker for worker in self._workers.values() if worker.is_available()]

        workers.sort(key=lambda worker: worker.started_at)

        return workers

    def count(
        self,
        *,
        status: WorkerStatus | None = None,
    ) -> int:
        """
        Count workers.

        Optionally filter by status.
        """

        if status is None:
            return len(self._workers)

        return sum(1 for worker in self._workers.values() if worker.status is status)

    def clear(self) -> None:
        """
        Remove all workers.

        Primarily intended for testing.
        """
        self._workers.clear()

    def __len__(self) -> int:
        """
        Return the number of workers.
        """
        return len(self._workers)

    def __contains__(self, worker_id: str) -> bool:
        """
        Determine whether the repository contains a worker.
        """
        return worker_id in self._workers

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation.
        """
        return f"{self.__class__.__name__}" f"(workers={len(self._workers)})"
