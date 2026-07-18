"""CLI-facing orchestration for starting and stopping worker processes.

Because ``queuectl worker start`` and ``queuectl worker stop`` are
separate command invocations (separate OS processes with no shared
memory), coordination between them happens through a PID file on
disk plus OS signals -- the same mechanism traditional Unix daemons
use.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from queuectl.config.schema import Settings
from queuectl.core.constants import (
    DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
    WORKER_PID_FILENAME,
)
from queuectl.infrastructure.logging.logger import get_logger
from queuectl.workers.lifecycle import install_signal_handlers
from queuectl.workers.shutdown import ShutdownSignal
from queuectl.workers.worker_pool import WorkerPool

_logger = get_logger("workers.worker_manager")


def _pid_file_path(base_dir: Path | None = None) -> Path:
    """Return the path to the worker PID file.

    Args:
        base_dir: Directory the PID file lives in. Defaults to the
            current working directory.

    Returns:
        Path: Path to the PID file (which may not yet exist).
    """
    directory = base_dir if base_dir is not None else Path.cwd()
    return directory / WORKER_PID_FILENAME


def _read_pids(pid_file: Path) -> list[int]:
    """Read worker PIDs previously written by :func:`start_workers`.

    Args:
        pid_file: Path to the PID file.

    Returns:
        list[int]: The recorded PIDs, or an empty list if the file
        does not exist or is empty.
    """
    if not pid_file.exists():
        return []
    content = pid_file.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return [int(line) for line in content.splitlines() if line.strip()]


def _process_is_alive(pid: int) -> bool:
    """Check whether a process with the given PID is still running.

    Args:
        pid: The process ID to check.

    Returns:
        bool: True if the process exists and is reachable.
    """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def start_workers(
    settings: Settings,
    *,
    count: int | None = None,
    base_dir: Path | None = None,
    block: bool = True,
    drain: bool = False,
) -> WorkerPool:
    """Start a pool of worker processes and record their PIDs.

    Args:
        settings: Configuration to run the workers with.
        count: Number of workers to start. Defaults to
            ``settings.worker_count``.
        base_dir: Directory to write the PID file in. Defaults to the
            current working directory.
        block: If True (the default), block in the foreground,
            forwarding SIGINT/SIGTERM to every worker and waiting for
            them to exit gracefully before returning. If False,
            workers are started and the PID file is written, but this
            function returns immediately (used by tests).
        drain: If True, every worker exits as soon as the queue is
            empty instead of polling indefinitely -- useful for
            batch/CI runs and for deterministic testing.

    Returns:
        WorkerPool: The pool of started worker processes.
    """
    worker_count = count or settings.worker_count
    worker_ids = [f"worker-{uuid.uuid4().hex[:8]}" for _ in range(worker_count)]

    pool = WorkerPool(settings)
    pool.start(worker_count, worker_ids=worker_ids, drain=drain)

    pid_file = _pid_file_path(base_dir)
    pid_file.write_text(
        "\n".join(str(pid) for pid in pool.pids()) + "\n",
        encoding="utf-8",
    )
    _logger.info("started %d worker(s), pids=%s", worker_count, pool.pids())

    if not block:
        return pool

    shutdown_signal = ShutdownSignal()
    install_signal_handlers(shutdown_signal)

    try:
        while not shutdown_signal.is_set() and not pool.all_stopped():
            shutdown_signal.wait(timeout=0.5)
    finally:
        stop_workers(
            base_dir=base_dir,
            timeout_seconds=DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
        )
        pid_file.unlink(missing_ok=True)

    return pool


def stop_workers(
    *,
    base_dir: Path | None = None,
    timeout_seconds: float = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
) -> int:
    """Gracefully stop every worker recorded in the PID file.

    Sends SIGTERM to each recorded, still-running PID and waits (up
    to ``timeout_seconds``) for it to exit before returning.

    Args:
        base_dir: Directory the PID file lives in. Defaults to the
            current working directory.
        timeout_seconds: Maximum total time to wait for workers to
            exit gracefully.

    Returns:
        int: The number of workers that were signaled.
    """
    import signal as signal_module

    pid_file = _pid_file_path(base_dir)
    pids = _read_pids(pid_file)
    live_pids = [pid for pid in pids if _process_is_alive(pid)]

    for pid in live_pids:
        try:
            os.kill(pid, signal_module.SIGTERM)
        except OSError:
            continue

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if all(not _process_is_alive(pid) for pid in live_pids):
            break
        time.sleep(0.1)

    pid_file.unlink(missing_ok=True)
    _logger.info("stopped %d worker(s)", len(live_pids))

    return len(live_pids)
