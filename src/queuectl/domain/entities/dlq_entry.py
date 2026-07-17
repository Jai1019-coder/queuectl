"""
Dead Letter Queue (DLQ) domain entity.

Represents a permanently failed job that can no longer be retried.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from queuectl.domain.value_objects.job_id import JobId


def _utcnow() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DlqEntry:
    """
    Domain entity representing a dead-letter queue entry.

    A DLQ entry records metadata about a job that has permanently
    failed after exhausting all retry attempts.
    """

    job_id: JobId
    failed_at: datetime
    reason: str
    retry_count: int
    error_message: str

    @classmethod
    def create(
        cls,
        *,
        job_id: JobId,
        reason: str,
        retry_count: int,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> "DlqEntry":
        """
        Create a new DLQ entry.

        Args:
            job_id:
                Identifier of the failed job.

            reason:
                Human-readable reason for moving to the DLQ.

            retry_count:
                Number of retries attempted.

            error_message:
                Original failure message.

            failed_at:
                Timestamp of failure.
                Defaults to current UTC time.

        Returns:
            DlqEntry
        """
        if not reason.strip():
            raise ValueError("reason cannot be empty.")

        if not error_message.strip():
            raise ValueError("error_message cannot be empty.")

        if retry_count < 0:
            raise ValueError("retry_count cannot be negative.")

        return cls(
            job_id=job_id,
            failed_at=failed_at or _utcnow(),
            reason=reason,
            retry_count=retry_count,
            error_message=error_message,
        )

    @property
    def is_retry_exhausted(self) -> bool:
        """
        DLQ entries always represent exhausted retries.

        Returns:
            bool
        """
        return True

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the DLQ entry.

        Returns:
            JSON-compatible dictionary.
        """
        return {
            "job_id": str(self.job_id),
            "failed_at": self.failed_at.isoformat(),
            "reason": self.reason,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "DlqEntry":
        """
        Deserialize a DLQ entry.
        """
        return cls(
            job_id=JobId.from_string(data["job_id"]),
            failed_at=datetime.fromisoformat(data["failed_at"]),
            reason=data["reason"],
            retry_count=data["retry_count"],
            error_message=data["error_message"],
        )

    def __repr__(self) -> str:
        return (
            "DlqEntry("
            f"job_id={self.job_id!r}, "
            f"retry_count={self.retry_count}, "
            f"reason={self.reason!r}"
            ")"
        )