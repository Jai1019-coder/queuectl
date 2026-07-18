"""
Retry Policy.

Encapsulates the business rules governing job retries.
"""

from __future__ import annotations

from dataclasses import dataclass

from queuectl.domain.value_objects.backoff_policy import BackoffPolicy


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """
    Defines retry rules for failed jobs.

    Attributes:
        max_retries:
            Maximum retry attempts before a job is considered dead.

        backoff:
            Strategy used to calculate retry delays.
    """

    max_retries: int = 3
    backoff: BackoffPolicy = BackoffPolicy()

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

    def should_retry(self, retry_count: int) -> bool:
        """
        Determine whether another retry is allowed.

        Args:
            retry_count:
                Number of retries already attempted.

        Returns:
            True if another retry is permitted.
        """
        if retry_count < 0:
            raise ValueError("retry_count cannot be negative.")

        return retry_count < self.max_retries

    def is_exhausted(self, retry_count: int) -> bool:
        """
        Returns True when retry limit has been reached.
        """
        return not self.should_retry(retry_count)

    def next_retry_delay(self, retry_count: int) -> int:
        """
        Calculate delay before the next retry.

        retry_count is the number of retries already completed.

        Example:

            retry_count = 0
            -> first retry
        """

        if not self.should_retry(retry_count):
            raise RuntimeError("Retry limit exceeded. No further retries allowed.")

        return self.backoff.get_delay(retry_count + 1)

    @property
    def has_retries(self) -> bool:
        """Whether retries are enabled."""
        return self.max_retries > 0

    def __str__(self) -> str:
        return (
            f"RetryPolicy("
            f"max_retries={self.max_retries}, "
            f"backoff={self.backoff}"
            f")"
        )
