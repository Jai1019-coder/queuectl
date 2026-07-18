"""QueueCTL exception hierarchy."""

from __future__ import annotations

from queuectl.exceptions.base import QueueCtlError
from queuectl.exceptions.config_exceptions import (
    InvalidConfigValueError,
    UnknownConfigKeyError,
)
from queuectl.exceptions.job_exceptions import (
    InvalidJobTransitionError,
    JobAlreadyExistsError,
    JobNotFoundError,
)
from queuectl.exceptions.worker_exceptions import (
    WorkerNotFoundError,
    WorkerShutdownTimeoutError,
    WorkerStartupError,
)

__all__ = [
    "QueueCtlError",
    "UnknownConfigKeyError",
    "InvalidConfigValueError",
    "JobNotFoundError",
    "JobAlreadyExistsError",
    "InvalidJobTransitionError",
    "WorkerNotFoundError",
    "WorkerStartupError",
    "WorkerShutdownTimeoutError",
]
