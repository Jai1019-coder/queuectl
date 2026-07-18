"""Default configuration values for QueueCTL.

Centralizing defaults here keeps :mod:`queuectl.config.schema` and
:mod:`queuectl.config.loader` free of magic literals, and keeps them
aligned with :class:`queuectl.domain.value_objects.backoff_policy.BackoffPolicy`
and :class:`queuectl.domain.policies.retry_policy.RetryPolicy`.
"""

from __future__ import annotations

DEFAULT_DATABASE_URL: str = "sqlite:///./queuectl.db"
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_STRATEGY: str = "exponential"
DEFAULT_BACKOFF_INITIAL_DELAY: int = 5
DEFAULT_BACKOFF_MULTIPLIER: float = 2.0
DEFAULT_BACKOFF_MAX_DELAY: int = 300
DEFAULT_WORKER_COUNT: int = 1
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_JOB_TIMEOUT_SECONDS: float = 0.0
DEFAULT_POLL_INTERVAL_SECONDS: float = 0.5

#: Name of the JSON file (relative to the current working directory)
#: that stores overrides written by ``queuectl config set``.
CONFIG_OVERRIDES_FILENAME: str = ".queuectl.config.json"
