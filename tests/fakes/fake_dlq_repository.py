"""In-memory fake DlqRepository for unit tests."""

from __future__ import annotations

from queuectl.domain.entities.dlq_entry import DlqEntry
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.dlq_repository import DlqRepository


class FakeDlqRepository(DlqRepository):
    """Simple dict-backed DlqRepository for use in unit tests."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._entries: dict[JobId, DlqEntry] = {}

    def save(self, entry: DlqEntry) -> None:
        """Persist a DLQ entry."""
        self._entries[entry.job_id] = entry

    def get(self, job_id: JobId) -> DlqEntry | None:
        """Retrieve a DLQ entry by Job ID."""
        return self._entries.get(job_id)

    def delete(self, job_id: JobId) -> None:
        """Delete a DLQ entry."""
        self._entries.pop(job_id, None)

    def exists(self, job_id: JobId) -> bool:
        """Determine whether a DLQ entry exists."""
        return job_id in self._entries

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DlqEntry]:
        """List DLQ entries."""
        entries = list(self._entries.values())[offset:]
        if limit is not None:
            entries = entries[:limit]
        return entries

    def count(self) -> int:
        """Count DLQ entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Remove all DLQ entries."""
        self._entries.clear()
