"""
Repository interface for Dead Letter Queue entries.

Defines the persistence contract for DlqEntry entities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from queuectl.domain.entities.dlq_entry import DlqEntry
from queuectl.domain.value_objects.job_id import JobId


class DlqRepository(ABC):
    """
    Abstract repository for Dead Letter Queue entries.
    """

    @abstractmethod
    def save(self, entry: DlqEntry) -> None:
        """
        Persist a DLQ entry.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: JobId) -> DlqEntry | None:
        """
        Retrieve a DLQ entry by Job ID.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, job_id: JobId) -> None:
        """
        Delete a DLQ entry.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, job_id: JobId) -> bool:
        """
        Determine whether a DLQ entry exists.
        """
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DlqEntry]:
        """
        List DLQ entries.
        """
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """
        Count DLQ entries.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all DLQ entries.

        Intended primarily for testing.
        """
        raise NotImplementedError
