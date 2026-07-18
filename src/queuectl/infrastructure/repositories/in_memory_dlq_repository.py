"""
In-memory implementation of DlqRepository.

Primarily intended for testing and local development.
"""

from __future__ import annotations

from queuectl.domain.entities.dlq_entry import DlqEntry
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.dlq_repository import DlqRepository


class InMemoryDlqRepository(DlqRepository):
    """
    In-memory implementation of the DlqRepository interface.

    Dead Letter Queue entries are stored in a dictionary keyed by JobId.
    """

    def __init__(self) -> None:
        """
        Initialize an empty DLQ repository.
        """
        self._entries: dict[JobId, DlqEntry] = {}

    def save(self, entry: DlqEntry) -> None:
        """
        Persist a DLQ entry.

        Raises:
            ValueError:
                If an entry with the same Job ID already exists.
        """
        if entry.job_id in self._entries:
            raise ValueError(f"DLQ entry for job {entry.job_id} already exists.")

        self._entries[entry.job_id] = entry

    def get(self, job_id: JobId) -> DlqEntry | None:
        """
        Retrieve a DLQ entry by Job ID.
        """
        return self._entries.get(job_id)

    def delete(self, job_id: JobId) -> None:
        """
        Delete a DLQ entry.

        Does nothing if the entry does not exist.
        """
        self._entries.pop(job_id, None)

    def exists(self, job_id: JobId) -> bool:
        """
        Determine whether a DLQ entry exists.
        """
        return job_id in self._entries

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DlqEntry]:
        """
        List DLQ entries ordered by failure time.
        """

        entries = sorted(
            self._entries.values(),
            key=lambda entry: entry.failed_at,
        )

        if offset > 0:
            entries = entries[offset:]

        if limit is not None:
            entries = entries[:limit]

        return entries

    def count(self) -> int:
        """
        Count DLQ entries.
        """
        return len(self._entries)

    def clear(self) -> None:
        """
        Remove all DLQ entries.

        Primarily intended for testing.
        """
        self._entries.clear()

    def __len__(self) -> int:
        """
        Return the number of DLQ entries.
        """
        return len(self._entries)

    def __contains__(self, job_id: JobId) -> bool:
        """
        Determine whether a DLQ entry exists.
        """
        return job_id in self._entries

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation.
        """
        return f"{self.__class__.__name__}" f"(entries={len(self._entries)})"
