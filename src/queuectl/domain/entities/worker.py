"""
Worker domain entity.

Represents a worker process capable of executing jobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.worker_status import WorkerStatus


def _utcnow() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


@dataclass(slots=True)
class Worker:
    """
    Domain entity representing a QueueCTL worker.
    """

    id: str
    hostname: str
    status: WorkerStatus
    started_at: datetime
    last_heartbeat: datetime
    max_concurrency: int = 1
    jobs_processed: int = 0
    current_job_id: JobId | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Worker id cannot be empty.")

        if not self.hostname.strip():
            raise ValueError("Hostname cannot be empty.")

        if self.max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than zero.")

    @classmethod
    def register(
        cls,
        worker_id: str,
        hostname: str,
        *,
        max_concurrency: int = 1,
        tags: list[str] | None = None,
        now: datetime | None = None,
    ) -> Worker:
        """
        Register a new worker.
        """
        timestamp = now or _utcnow()

        return cls(
            id=worker_id,
            hostname=hostname,
            status=WorkerStatus.ONLINE,
            started_at=timestamp,
            last_heartbeat=timestamp,
            max_concurrency=max_concurrency,
            tags=tags or [],
        )

    def heartbeat(
        self,
        *,
        now: datetime | None = None,
    ) -> None:
        """
        Update heartbeat timestamp.
        """
        self.last_heartbeat = now or _utcnow()

    def assign_job(
        self,
        job_id: JobId,
    ) -> None:
        """
        Assign a job to this worker.
        """
        if self.status != WorkerStatus.ONLINE:
            raise ValueError("Only ONLINE workers can accept jobs.")

        self.current_job_id = job_id
        self.status = WorkerStatus.BUSY

    def complete_job(self) -> None:
        """
        Mark current job completed.
        """
        if self.current_job_id is None:
            raise ValueError("Worker has no assigned job.")

        self.current_job_id = None
        self.jobs_processed += 1
        self.status = WorkerStatus.ONLINE

    def fail_job(self) -> None:
        """
        Mark current job as failed.
        """
        if self.current_job_id is None:
            raise ValueError("Worker has no assigned job.")

        self.current_job_id = None
        self.status = WorkerStatus.ONLINE

    def set_offline(self) -> None:
        """
        Mark worker offline.
        """
        self.status = WorkerStatus.OFFLINE

    def set_online(self) -> None:
        """
        Bring worker online.
        """
        if self.current_job_id is not None:
            raise ValueError("Worker still owns a job.")

        self.status = WorkerStatus.ONLINE

    def is_available(self) -> bool:
        """
        Whether worker can accept jobs.
        """
        return self.status.is_available

    def is_online(self) -> bool:
        """
        Whether worker is online.
        """
        return self.status.is_online

    def touch(
        self,
        *,
        now: datetime | None = None,
    ) -> None:
        """
        Refresh heartbeat.
        """
        self.last_heartbeat = now or _utcnow()

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize worker.
        """
        return {
            "id": self.id,
            "hostname": self.hostname,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "max_concurrency": self.max_concurrency,
            "jobs_processed": self.jobs_processed,
            "current_job_id": (
                str(self.current_job_id) if self.current_job_id else None
            ),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> Worker:
        """
        Deserialize worker.
        """
        return cls(
            id=data["id"],
            hostname=data["hostname"],
            status=WorkerStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
            max_concurrency=data["max_concurrency"],
            jobs_processed=data["jobs_processed"],
            current_job_id=(
                JobId.from_string(data["current_job_id"])
                if data["current_job_id"]
                else None
            ),
            tags=list(data.get("tags", [])),
        )

    def __repr__(self) -> str:
        return (
            f"Worker("
            f"id={self.id!r}, "
            f"status={self.status.value!r}, "
            f"jobs_processed={self.jobs_processed}, "
            f"current_job_id={self.current_job_id!r}"
            f")"
        )
