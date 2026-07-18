"""Worker heartbeat recording."""

from __future__ import annotations

from queuectl.core.interfaces import Clock
from queuectl.domain.entities.worker import Worker
from queuectl.repositories.worker_repository import WorkerRepository


class HeartbeatRecorder:
    """Persists periodic liveness updates for a worker.

    A stale ``last_heartbeat`` is how an operator (or a future
    monitoring feature) distinguishes a worker that is merely idle
    from one that has crashed without deregistering itself.
    """

    def __init__(
        self,
        worker_repository: WorkerRepository,
        clock: Clock,
    ) -> None:
        """Initialize the recorder.

        Args:
            worker_repository: Repository used to persist the worker.
            clock: Source of the current time.
        """
        self._worker_repository = worker_repository
        self._clock = clock

    def beat(self, worker: Worker) -> None:
        """Refresh and persist a worker's heartbeat timestamp.

        Args:
            worker: The worker to update. Mutated in place.
        """
        worker.heartbeat(now=self._clock.now())
        self._worker_repository.update(worker)
