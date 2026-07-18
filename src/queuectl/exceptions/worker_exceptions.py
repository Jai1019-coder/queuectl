"""Worker-related exceptions."""

from __future__ import annotations

from queuectl.exceptions.base import QueueCtlError


class WorkerNotFoundError(QueueCtlError):
    """Raised when a referenced worker does not exist."""


class WorkerStartupError(QueueCtlError):
    """Raised when a worker process fails to start."""


class WorkerShutdownTimeoutError(QueueCtlError):
    """Raised when a worker does not shut down within the deadline."""
