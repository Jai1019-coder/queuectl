"""Configuration-related exceptions."""

from __future__ import annotations

from queuectl.exceptions.base import QueueCtlError


class UnknownConfigKeyError(QueueCtlError):
    """Raised when ``queuectl config set`` receives an unknown key."""


class InvalidConfigValueError(QueueCtlError):
    """Raised when a configuration value fails validation."""
