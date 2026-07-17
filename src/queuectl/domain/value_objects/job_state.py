"""
Job state value object.

Defines the lifecycle states through which a QueueCTL job transitions.
"""

from __future__ import annotations

from enum import StrEnum


class JobState(StrEnum):
    """
    Represents the lifecycle state of a job.

    Lifecycle

        PENDING
            │
            ▼
        PROCESSING
          │      │
          │      ▼
          │  COMPLETED
          │
          ▼
        FAILED
          │
          ├──── retry ─────► PENDING
          │
          ▼
         DEAD
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"

    @property
    def is_terminal(self) -> bool:
        """Return True if no more state transitions are allowed."""
        return self in (
            JobState.COMPLETED,
            JobState.DEAD,
        )

    @property
    def can_retry(self) -> bool:
        """Return True if the job is eligible for retry."""
        return self is JobState.FAILED

    @property
    def can_be_claimed(self) -> bool:
        """Return True if a worker may claim this job."""
        return self is JobState.PENDING

    @property
    def is_active(self) -> bool:
        """Return True while a worker owns the job."""
        return self is JobState.PROCESSING

    def __str__(self) -> str:
        return self.value