"""In-memory fake WorkerRepository for unit tests."""

from __future__ import annotations

from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.worker_status import WorkerStatus
from queuectl.repositories.worker_repository import WorkerRepository


class FakeWorkerRepository(WorkerRepository):
    """Simple dict-backed WorkerRepository for use in unit tests."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._workers: dict[str, Worker] = {}

    def save(self, worker: Worker) -> None:
        """Persist a new worker."""
        self._workers[worker.id] = worker

    def get(self, worker_id: str) -> Worker | None:
        """Retrieve a worker by its identifier."""
        return self._workers.get(worker_id)

    def update(self, worker: Worker) -> None:
        """Persist changes to an existing worker."""
        self._workers[worker.id] = worker

    def delete(self, worker_id: str) -> None:
        """Remove a worker."""
        self._workers.pop(worker_id, None)

    def exists(self, worker_id: str) -> bool:
        """Check whether a worker exists."""
        return worker_id in self._workers

    def list(
        self,
        *,
        status: WorkerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Worker]:
        """List workers, optionally filtered by status."""
        workers = list(self._workers.values())
        if status is not None:
            workers = [w for w in workers if w.status is status]
        workers = workers[offset:]
        if limit is not None:
            workers = workers[:limit]
        return workers

    def list_available(self) -> list[Worker]:
        """Return workers currently available to execute jobs."""
        return [w for w in self._workers.values() if w.is_available()]

    def count(self, *, status: WorkerStatus | None = None) -> int:
        """Count workers, optionally filtered by status."""
        return len(self.list(status=status))

    def clear(self) -> None:
        """Remove all workers."""
        self._workers.clear()
