"""
Backoff Policy Value Object.

Defines how retry delays are calculated for failed jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import pow


class BackoffStrategy(StrEnum):
    """Supported retry backoff strategies."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass(frozen=True, slots=True)
class BackoffPolicy:
    """
    Immutable value object describing retry delay behavior.

    Attributes:
        strategy:
            Retry strategy.

        initial_delay:
            Delay before first retry (seconds).

        multiplier:
            Growth factor.

        max_delay:
            Maximum allowed delay.
    """

    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    initial_delay: int = 5
    multiplier: float = 2.0
    max_delay: int = 300

    def __post_init__(self) -> None:
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be greater than zero.")

        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1.")

        if self.max_delay < self.initial_delay:
            raise ValueError(
                "max_delay cannot be smaller than initial_delay."
            )

    def get_delay(self, attempt: int) -> int:
        """
        Compute retry delay.

        Args:
            attempt:
                Retry attempt number.

                First retry = 1

        Returns:
            Delay in seconds.
        """

        if attempt <= 0:
            raise ValueError("attempt must be >= 1")

        if self.strategy is BackoffStrategy.FIXED:
            delay = self.initial_delay

        elif self.strategy is BackoffStrategy.LINEAR:
            delay = self.initial_delay * attempt

        else:
            delay = self.initial_delay * pow(
                self.multiplier,
                attempt - 1,
            )

        return int(min(delay, self.max_delay))

    @property
    def is_exponential(self) -> bool:
        return self.strategy is BackoffStrategy.EXPONENTIAL

    @property
    def is_linear(self) -> bool:
        return self.strategy is BackoffStrategy.LINEAR

    @property
    def is_fixed(self) -> bool:
        return self.strategy is BackoffStrategy.FIXED

    def __str__(self) -> str:
        return (
            f"{self.strategy.value}"
            f"(initial={self.initial_delay}, "
            f"multiplier={self.multiplier}, "
            f"max={self.max_delay})"
        )