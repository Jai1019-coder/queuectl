"""Configuration schema for QueueCTL.

Defines the strongly-typed settings model used throughout the
application. Values are sourced from, in increasing priority order:
built-in defaults, a `.env` file, environment variables, and a local
JSON overrides file written by ``queuectl config set``.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from queuectl.config.defaults import (
    DEFAULT_BACKOFF_INITIAL_DELAY,
    DEFAULT_BACKOFF_MAX_DELAY,
    DEFAULT_BACKOFF_MULTIPLIER,
    DEFAULT_BACKOFF_STRATEGY,
    DEFAULT_DATABASE_URL,
    DEFAULT_JOB_TIMEOUT_SECONDS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_WORKER_COUNT,
)

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_BACKOFF_STRATEGIES = {"fixed", "linear", "exponential"}


class Settings(BaseSettings):
    """Runtime configuration for QueueCTL.

    Attributes:
        database_url: SQLAlchemy/QueueCTL-style database URL. Only the
            ``sqlite:///<path>`` form is currently used; the path
            portion is what backs the SQLite connection.
        max_retries: Default maximum retry attempts for a job before
            it is moved to the Dead Letter Queue.
        backoff_strategy: One of ``"fixed"``, ``"linear"``, or
            ``"exponential"``.
        backoff_initial_delay: Delay, in seconds, before the first
            retry.
        backoff_multiplier: Growth factor applied between retries
            when using the linear or exponential strategies.
        backoff_max_delay: Upper bound, in seconds, on any computed
            retry delay.
        worker_count: Default number of worker processes started by
            ``queuectl worker start`` when ``--count`` is omitted.
        log_level: Logging verbosity for the application logger.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default=DEFAULT_DATABASE_URL)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=0)
    backoff_strategy: str = Field(default=DEFAULT_BACKOFF_STRATEGY)
    backoff_initial_delay: int = Field(default=DEFAULT_BACKOFF_INITIAL_DELAY, gt=0)
    backoff_multiplier: float = Field(default=DEFAULT_BACKOFF_MULTIPLIER, ge=1)
    backoff_max_delay: int = Field(default=DEFAULT_BACKOFF_MAX_DELAY, gt=0)
    worker_count: int = Field(default=DEFAULT_WORKER_COUNT, gt=0)
    log_level: str = Field(default=DEFAULT_LOG_LEVEL)
    job_timeout_seconds: float = Field(default=DEFAULT_JOB_TIMEOUT_SECONDS, ge=0)
    poll_interval_seconds: float = Field(default=DEFAULT_POLL_INTERVAL_SECONDS, gt=0)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        """Normalize and validate the configured log level.

        Args:
            value: The raw log level string.

        Returns:
            str: The upper-cased, validated log level.

        Raises:
            ValueError: If the level is not a recognized Python
                logging level name.
        """
        normalized = value.strip().upper()
        if normalized not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"log_level must be one of {sorted(_VALID_LOG_LEVELS)}, "
                f"got {value!r}."
            )
        return normalized

    @field_validator("backoff_strategy")
    @classmethod
    def _validate_backoff_strategy(cls, value: str) -> str:
        """Normalize and validate the configured backoff strategy.

        Args:
            value: The raw backoff strategy string.

        Returns:
            str: The lower-cased, validated backoff strategy.

        Raises:
            ValueError: If the strategy is not recognized.
        """
        normalized = value.strip().lower()
        if normalized not in _VALID_BACKOFF_STRATEGIES:
            raise ValueError(
                f"backoff_strategy must be one of "
                f"{sorted(_VALID_BACKOFF_STRATEGIES)}, got {value!r}."
            )
        return normalized

    @property
    def database_path(self) -> str:
        """Return the filesystem path portion of ``database_url``.

        Returns:
            str: The SQLite file path, or ``:memory:`` for an
            in-memory database.

        Raises:
            ValueError: If ``database_url`` is not a supported SQLite
                URL of the form ``sqlite:///<path>``.
        """
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError(
                f"Unsupported database_url {self.database_url!r}; "
                f"expected a URL starting with {prefix!r}."
            )
        path = self.database_url[len(prefix) :]
        return path or ":memory:"

    @property
    def resolved_job_timeout(self) -> float | None:
        """Return the effective per-job timeout.

        Returns:
            float | None: ``None`` if ``job_timeout_seconds`` is ``0``
            (meaning "no timeout"), otherwise the configured value.
        """
        return self.job_timeout_seconds if self.job_timeout_seconds > 0 else None
