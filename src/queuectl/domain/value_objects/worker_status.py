"""
Worker Status value object.

Represents the lifecycle state of a QueueCTL worker.
"""

from __future__ import annotations

from enum import StrEnum


class WorkerStatus(StrEnum):
    """
    Enumeration representing the status of a worker.

    States:
        ONLINE:
            Worker is idle and ready to accept jobs.

        BUSY:
            Worker is currently processing a job.

        OFFLINE:
            Worker is unavailable and cannot accept jobs.
    """

    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"

    @property
    def is_online(self) -> bool:
        """
        Return True if the worker is online.

        Returns:
            bool: True for ONLINE and BUSY workers.
        """
        return self is not WorkerStatus.OFFLINE

    @property
    def is_available(self) -> bool:
        """
        Return True if the worker can accept a new job.

        Returns:
            bool: True only for ONLINE workers.
        """
        return self is WorkerStatus.ONLINE

    @property
    def is_busy(self) -> bool:
        """
        Return True if the worker is processing a job.

        Returns:
            bool: True only for BUSY workers.
        """
        return self is WorkerStatus.BUSY

    @property
    def is_offline(self) -> bool:
        """
        Return True if the worker is offline.

        Returns:
            bool: True only for OFFLINE workers.
        """
        return self is WorkerStatus.OFFLINE

    def __str__(self) -> str:
        """
        Return the string representation.

        Returns:
            str: Status value.
        """
        return self.value
