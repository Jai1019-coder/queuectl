"""Domain entity representing a background job in the QueueCTL system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState


def _utcnow() -> datetime:
    """Return the current UTC timestamp.

    Returns:
        datetime: The current time expressed in UTC with timezone info.
    """
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Job:
    """Aggregate root representing a single background job.

    A ``Job`` encapsulates all state and behavior related to the
    lifecycle of a unit of work submitted to QueueCTL. It exposes
    explicit, validated state-transition methods and never allows an
    illegal transition to occur silently. Retry scheduling policy
    (how long to wait, how many attempts are allowed) is deliberately
    kept out of this entity; callers such as ``RetryPolicy`` compute the
    delay and retry eligibility, and the entity only exposes the
    primitive operations needed to apply that decision.

    Attributes:
        id: The unique identifier of the job.
        name: The human-readable name of the job (typically the command
            or task identifier to execute).
        payload: Arbitrary JSON-serializable data associated with the job.
        priority: The scheduling priority of the job. Higher values are
            more urgent. Must be greater than or equal to zero.
        state: The current lifecycle state of the job.
        retry_count: The number of times the job has been retried.
        created_at: The UTC timestamp at which the job was created.
        updated_at: The UTC timestamp of the last modification.
        available_at: The UTC timestamp at which the job becomes eligible
            for claiming by a worker.
        started_at: The UTC timestamp at which the job most recently
            started processing, or ``None`` if it has never started.
        completed_at: The UTC timestamp at which the job completed
            successfully, or ``None`` if it has not completed.
        worker_id: The identifier of the worker currently or most
            recently assigned to the job, or ``None`` if unassigned.
        error_message: The error message from the most recent failure,
            or ``None`` if the job has not failed.
    """

    id: JobId
    name: str
    payload: dict[str, Any]
    priority: int
    state: JobState
    retry_count: int
    created_at: datetime
    updated_at: datetime
    available_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worker_id: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants after initialization.

        Raises:
            ValueError: If ``priority`` is negative.
        """
        if self.priority < 0:
            raise ValueError("priority must be greater than or equal to 0.")

    @classmethod
    def create(
        cls,
        name: str,
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        job_id: JobId | None = None,
        *,
        now: datetime | None = None,
    ) -> "Job":
        """Create a new job in the ``PENDING`` state.

        Args:
            name: The human-readable name of the job. Must not be empty.
            payload: Arbitrary JSON-serializable data for the job.
                Defaults to an empty dictionary.
            priority: The scheduling priority of the job. Must be
                greater than or equal to zero. Defaults to ``0``.
            job_id: An explicit identifier for the job. If ``None``, a
                new identifier is generated via :meth:`JobId.generate`.
            now: The reference timestamp to stamp creation with.
                Defaults to the current UTC time.

        Returns:
            Job: A newly constructed job in the ``PENDING`` state, with
            ``available_at`` equal to its ``created_at``.

        Raises:
            ValueError: If ``name`` is empty or ``priority`` is negative.
        """
        if not name:
            raise ValueError("name must not be empty.")
        reference = now if now is not None else _utcnow()
        return cls(
            id=job_id if job_id is not None else JobId.generate(),
            name=name,
            payload=payload if payload is not None else {},
            priority=priority,
            state=JobState.PENDING,
            retry_count=0,
            created_at=reference,
            updated_at=reference,
            available_at=reference,
        )

    def can_be_claimed(self, *, now: datetime | None = None) -> bool:
        """Determine whether the job is eligible to be claimed by a worker.

        Args:
            now: The reference timestamp to evaluate availability
                against. Defaults to the current UTC time.

        Returns:
            bool: ``True`` if the job is ``PENDING`` and its
            ``available_at`` timestamp has elapsed, ``False`` otherwise.
        """
        reference = now if now is not None else _utcnow()
        return self.state is JobState.PENDING and self.available_at <= reference

    def claim(self, worker_id: str, *, now: datetime | None = None) -> None:
        """Assign a worker to the job and transition it to ``PROCESSING``.

        Args:
            worker_id: The identifier of the worker claiming the job.
                Must not be empty.
            now: The reference timestamp used to evaluate eligibility
                and to stamp the transition. Defaults to the current
                UTC time.

        Raises:
            ValueError: If ``worker_id`` is empty, or if the job cannot
                currently be claimed (not ``PENDING`` or not yet
                available).
        """
        if not worker_id:
            raise ValueError("worker_id must not be empty.")
        reference = now if now is not None else _utcnow()
        if not self.can_be_claimed(now=reference):
            raise ValueError(
                f"Job {self.id} cannot be claimed while in state {self.state}."
            )
        self.worker_id = worker_id
        self._transition_to_processing(now=reference)

    def mark_processing(self, *, now: datetime | None = None) -> None:
        """Explicitly transition the job to the ``PROCESSING`` state.

        Args:
            now: The reference timestamp to stamp the transition with.
                Defaults to the current UTC time.

        Raises:
            ValueError: If the job is not currently ``PENDING`` (this
                includes the case where the job is already
                ``PROCESSING``).
        """
        reference = now if now is not None else _utcnow()
        if self.state is not JobState.PENDING:
            raise ValueError(
                f"Job {self.id} cannot be marked as processing from state "
                f"{self.state}."
            )
        self._transition_to_processing(now=reference)

    def _transition_to_processing(self, *, now: datetime) -> None:
        """Perform the internal transition into the ``PROCESSING`` state.

        Args:
            now: The timestamp to record as the start time of processing.
        """
        self.state = JobState.PROCESSING
        self.started_at = now
        self.error_message = None
        self.updated_at = now

    def mark_completed(self, *, now: datetime | None = None) -> None:
        """Transition the job to the ``COMPLETED`` state.

        Args:
            now: The reference timestamp to stamp the completion with.
                Defaults to the current UTC time.

        Raises:
            ValueError: If the job is not currently ``PROCESSING``.
        """
        if self.state is not JobState.PROCESSING:
            raise ValueError(
                f"Job {self.id} cannot be completed from state {self.state}."
            )
        reference = now if now is not None else _utcnow()
        self.state = JobState.COMPLETED
        self.completed_at = reference
        self.error_message = None
        self.updated_at = reference

    def mark_failed(
        self, error_message: str, *, now: datetime | None = None
    ) -> None:
        """Transition the job to the ``FAILED`` state.

        Args:
            error_message: A description of the failure. Must not be
                empty.
            now: The reference timestamp to stamp the failure with.
                Defaults to the current UTC time.

        Raises:
            ValueError: If ``error_message`` is empty, or if the job is
                not currently ``PROCESSING`` (this includes the case
                where the job is already ``COMPLETED``).
        """
        if not error_message:
            raise ValueError("error_message must not be empty.")
        if self.state is not JobState.PROCESSING:
            raise ValueError(
                f"Job {self.id} cannot be failed from state {self.state}."
            )
        reference = now if now is not None else _utcnow()
        self.state = JobState.FAILED
        self.error_message = error_message
        self.updated_at = reference

    def increment_retry(self, *, now: datetime | None = None) -> None:
        """Increment the retry counter without changing the job state.

        Args:
            now: The reference timestamp to stamp the update with.
                Defaults to the current UTC time.

        Raises:
            ValueError: If the job is in a terminal ``COMPLETED`` or
                ``DEAD`` state.
        """
        self._guard_not_finalized(action="retried")
        reference = now if now is not None else _utcnow()
        self.retry_count += 1
        self.updated_at = reference

    def schedule_retry(
        self, delay_seconds: float, *, now: datetime | None = None
    ) -> None:
        """Reschedule the job for a future retry attempt.

        Transitions the job back to ``PENDING`` and pushes its
        ``available_at`` timestamp into the future by ``delay_seconds``.
        This method does not modify ``retry_count``; callers must invoke
        :meth:`increment_retry` separately if the attempt should be
        counted.

        Args:
            delay_seconds: The number of seconds to wait before the job
                becomes available again. Must be greater than or equal
                to zero.
            now: The reference timestamp used as the base for computing
                the new ``available_at``. Defaults to the current UTC
                time.

        Raises:
            ValueError: If ``delay_seconds`` is negative, or if the job
                is in a terminal ``COMPLETED`` or ``DEAD`` state.
        """
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be greater than or equal to 0.")
        self._guard_not_finalized(action="rescheduled")
        reference = now if now is not None else _utcnow()
        self.state = JobState.PENDING
        self.available_at = reference + timedelta(seconds=delay_seconds)
        self.updated_at = reference

    def move_to_dead(self, *, now: datetime | None = None) -> None:
        """Permanently move the job to the ``DEAD`` state.

        Args:
            now: The reference timestamp to stamp the transition with.
                Defaults to the current UTC time.

        Raises:
            ValueError: If the job is currently ``COMPLETED``.
        """
        if self.state is JobState.COMPLETED:
            raise ValueError(
                f"Job {self.id} cannot be moved to DEAD from COMPLETED."
            )
        reference = now if now is not None else _utcnow()
        self.state = JobState.DEAD
        self.updated_at = reference

    def reset(self, *, now: datetime | None = None) -> None:
        """Reset the job to a fresh ``PENDING`` state.

        Clears all execution metadata (worker assignment, processing and
        completion timestamps, error message, and retry count) and makes
        the job immediately available for claiming.

        Args:
            now: The reference timestamp to stamp the reset with.
                Defaults to the current UTC time.
        """
        reference = now if now is not None else _utcnow()
        self.state = JobState.PENDING
        self.retry_count = 0
        self.worker_id = None
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.available_at = reference
        self.updated_at = reference

    def is_terminal(self) -> bool:
        """Determine whether the job is in a terminal state.

        Returns:
            bool: ``True`` if the job is ``COMPLETED`` or ``DEAD``,
            ``False`` otherwise.
        """
        return self.state.is_terminal

    def is_completed(self) -> bool:
        """Determine whether the job has completed successfully.

        Returns:
            bool: ``True`` if the job state is ``COMPLETED``.
        """
        return self.state is JobState.COMPLETED

    def is_failed(self) -> bool:
        """Determine whether the job is currently in the ``FAILED`` state.

        Returns:
            bool: ``True`` if the job state is ``FAILED``.
        """
        return self.state is JobState.FAILED

    def is_dead(self) -> bool:
        """Determine whether the job has been moved to the dead letter state.

        Returns:
            bool: ``True`` if the job state is ``DEAD``.
        """
        return self.state is JobState.DEAD

    def is_processing(self) -> bool:
        """Determine whether the job is currently being processed.

        Returns:
            bool: ``True`` if the job state is ``PROCESSING``.
        """
        return self.state is JobState.PROCESSING

    def touch(self, *, now: datetime | None = None) -> None:
        """Refresh the ``updated_at`` timestamp without altering state.

        Args:
            now: The reference timestamp to stamp the update with.
                Defaults to the current UTC time.
        """
        self.updated_at = now if now is not None else _utcnow()

    def _guard_not_finalized(self, *, action: str) -> None:
        """Raise if the job is in a terminal state that forbids ``action``.

        Args:
            action: A human-readable description of the attempted
                action, used in the error message.

        Raises:
            ValueError: If the job is ``COMPLETED`` or ``DEAD``.
        """
        if self.is_terminal():
            raise ValueError(
                f"Job {self.id} cannot be {action} from terminal state "
                f"{self.state}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the job into a JSON-compatible dictionary.

        Returns:
            dict[str, Any]: A dictionary representation of the job with
            all values expressed as JSON-serializable primitives. The
            ``id`` field is serialized as a string, ``state`` as its
            string value, and all datetimes as ISO 8601 strings.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "payload": self.payload,
            "priority": self.priority,
            "state": self.state.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "worker_id": self.worker_id,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Deserialize a job from a JSON-compatible dictionary.

        Args:
            data: A dictionary previously produced by :meth:`to_dict`.

        Returns:
            Job: The reconstructed job instance.

        Raises:
            KeyError: If a required field is missing from ``data``.
            ValueError: If a field contains an invalid value.
        """
        return cls(
            id=JobId.from_string(data["id"]),
            name=data["name"],
            payload=data["payload"],
            priority=data["priority"],
            state=JobState(data["state"]),
            retry_count=data["retry_count"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            available_at=datetime.fromisoformat(data["available_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            worker_id=data.get("worker_id"),
            error_message=data.get("error_message"),
        )

    def __repr__(self) -> str:
        """Return an unambiguous string representation of the job.

        Returns:
            str: A string including the job's id, name, state, priority,
            and retry count.
        """
        return (
            f"Job(id={self.id!r}, name={self.name!r}, state={self.state!r}, "
            f"priority={self.priority}, retry_count={self.retry_count})"
        )
