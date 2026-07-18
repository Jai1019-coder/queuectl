"""Multi-process worker pool.

Spawns N independent OS processes, each running a
:class:`~queuectl.workers.worker.WorkerRuntime` loop against its own
database connection. Using separate processes (rather than threads)
gives QueueCTL true CPU/process-level parallelism and matches the
assignment's "multiple worker processes" requirement.
"""

from __future__ import annotations

import multiprocessing

from queuectl.config.schema import Settings
from queuectl.core.container import build_container
from queuectl.infrastructure.logging.logger import configure_logging
from queuectl.workers.lifecycle import install_signal_handlers
from queuectl.workers.shutdown import ShutdownSignal
from queuectl.workers.worker import WorkerRuntime


def _run_worker_process(worker_id: str, settings: Settings, drain: bool) -> None:
    """Entry point executed inside each spawned worker process.

    Builds an independent container (and therefore an independent
    SQLite connection, since connections cannot cross process
    boundaries) and runs the worker loop until this process receives
    SIGINT/SIGTERM (or, in drain mode, until no job is available).

    Args:
        worker_id: Unique identifier for this worker process.
        settings: Configuration to build the container from.
        drain: If True, exit as soon as the queue is empty instead of
            polling indefinitely.
    """
    configure_logging(settings.log_level)

    shutdown_signal = ShutdownSignal()
    install_signal_handlers(shutdown_signal)

    with build_container(settings) as container:
        runtime = WorkerRuntime(
            worker_id=worker_id,
            process_job=container.process_job,
            complete_job=container.complete_job,
            fail_job=container.fail_job,
            retry_job=container.retry_job,
            move_to_dlq=container.move_to_dlq,
            worker_repository=container.worker_repository,
            command_executor=container.command_executor,
            retry_policy=container.retry_policy,
            clock=container.clock,
            shutdown_signal=shutdown_signal,
            poll_interval_seconds=settings.poll_interval_seconds,
            job_timeout_seconds=settings.resolved_job_timeout,
            stop_when_idle=drain,
        )
        runtime.run()


class WorkerPool:
    """Owns a fixed-size set of worker processes.

    Attributes:
        settings: Configuration passed through to every worker
            process.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize an empty pool.

        Args:
            settings: Configuration passed through to every worker
                process.
        """
        self.settings = settings
        self._processes: list[multiprocessing.Process] = []

    def start(
        self,
        count: int,
        *,
        worker_ids: list[str],
        drain: bool = False,
    ) -> None:
        """Spawn ``count`` worker processes.

        Args:
            count: Number of worker processes to start.
            worker_ids: Unique identifiers, one per worker, of length
                ``count``.
            drain: If True, each worker exits as soon as the queue is
                empty instead of polling indefinitely.

        Raises:
            ValueError: If ``count`` is not positive, or
                ``worker_ids`` does not have exactly ``count``
                entries.
        """
        if count <= 0:
            raise ValueError("count must be greater than zero.")
        if len(worker_ids) != count:
            raise ValueError("worker_ids must have exactly `count` entries.")

        # A context that supports 'spawn' keeps behavior identical
        # across platforms (required on Windows, safest everywhere).
        context = multiprocessing.get_context("spawn")

        for worker_id in worker_ids:
            process = context.Process(
                target=_run_worker_process,
                args=(worker_id, self.settings, drain),
                name=f"queuectl-worker-{worker_id}",
                daemon=False,
            )
            process.start()
            self._processes.append(process)

    def pids(self) -> list[int]:
        """Return the OS process IDs of every running worker.

        Returns:
            list[int]: PIDs of all spawned worker processes that have
            an assigned PID.
        """
        return [p.pid for p in self._processes if p.pid is not None]

    def join(self, timeout: float | None = None) -> None:
        """Wait for every worker process to exit.

        Args:
            timeout: Maximum total time to wait, in seconds. ``None``
                waits indefinitely.
        """
        for process in self._processes:
            process.join(timeout=timeout)

    def terminate(self) -> None:
        """Forcibly terminate any worker processes still running.

        Used as a last resort if a worker does not exit within the
        graceful shutdown deadline.
        """
        for process in self._processes:
            if process.is_alive():
                process.terminate()
        for process in self._processes:
            process.join()

    def all_stopped(self) -> bool:
        """Return whether every worker process has exited.

        Returns:
            bool: True if no worker process is still alive.
        """
        return all(not p.is_alive() for p in self._processes)


__all__ = ["WorkerPool"]
