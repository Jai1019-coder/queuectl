"""Shared constants for QueueCTL's composition root and CLI."""

from __future__ import annotations

#: Default polling interval (seconds) a worker sleeps for when the
#: queue has no available job.
DEFAULT_POLL_INTERVAL_SECONDS: float = 0.5

#: Default maximum time (seconds) a job's command may run before
#: being forcibly terminated. ``None`` disables the timeout.
DEFAULT_JOB_TIMEOUT_SECONDS: float | None = None

#: Default number of seconds ``queuectl worker stop`` waits for
#: workers to exit gracefully before giving up.
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS: float = 30.0

#: Filename (relative to the current working directory) used to
#: track running worker process IDs between ``worker start`` and
#: ``worker stop`` invocations.
WORKER_PID_FILENAME: str = ".queuectl.worker.pid"
