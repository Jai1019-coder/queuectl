"""Cross-cutting interfaces shared across QueueCTL's layers.

These protocols/ABCs let the application and worker layers depend on
abstractions rather than concrete infrastructure, keeping the
dependency arrows pointing inward as required by Clean Architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class Clock(ABC):
    """Abstraction over "the current time" for deterministic testing."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current time.

        Returns:
            datetime: The current time, timezone-aware.
        """
        raise NotImplementedError


class SystemClock(Clock):
    """A Clock backed by the real system time (UTC)."""

    def now(self) -> datetime:
        """Return the current UTC time.

        Returns:
            datetime: ``datetime.now(timezone.utc)``.
        """
        return datetime.now(UTC)
