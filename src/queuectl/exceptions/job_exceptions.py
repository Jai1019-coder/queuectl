"""Job-related exceptions."""

from __future__ import annotations

from queuectl.exceptions.base import QueueCtlError


class JobNotFoundError(QueueCtlError):
    """Raised when a referenced job does not exist."""


class JobAlreadyExistsError(QueueCtlError):
    """Raised when attempting to persist a job with a duplicate id."""


class InvalidJobTransitionError(QueueCtlError):
    """Raised when an illegal job state transition is attempted."""
