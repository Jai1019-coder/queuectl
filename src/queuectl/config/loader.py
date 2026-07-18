"""Configuration loading and persistence for QueueCTL.

QueueCTL settings are resolved in increasing priority order:

1. Built-in defaults (:mod:`queuectl.config.defaults`).
2. A ``.env`` file in the current working directory.
3. Process environment variables.
4. A local JSON overrides file written by ``queuectl config set``,
   which always takes precedence so that explicit configuration
   changes persist across process restarts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from queuectl.config.defaults import CONFIG_OVERRIDES_FILENAME
from queuectl.config.schema import Settings
from queuectl.exceptions.config_exceptions import UnknownConfigKeyError

#: Maps the hyphenated CLI key (e.g. ``max-retries``) used by
#: ``queuectl config set`` to the underlying :class:`Settings` field
#: name (e.g. ``max_retries``).
CLI_KEY_TO_FIELD: dict[str, str] = {
    "database-url": "database_url",
    "max-retries": "max_retries",
    "backoff-strategy": "backoff_strategy",
    "backoff-initial-delay": "backoff_initial_delay",
    "backoff-multiplier": "backoff_multiplier",
    "backoff-max-delay": "backoff_max_delay",
    "worker-count": "worker_count",
    "log-level": "log_level",
    "job-timeout": "job_timeout_seconds",
    "poll-interval": "poll_interval_seconds",
}

_FIELD_TYPES: dict[str, type] = {
    "database_url": str,
    "max_retries": int,
    "backoff_strategy": str,
    "backoff_initial_delay": int,
    "backoff_multiplier": float,
    "backoff_max_delay": int,
    "worker_count": int,
    "log_level": str,
    "job_timeout_seconds": float,
    "poll_interval_seconds": float,
}


def get_overrides_path(base_dir: Path | None = None) -> Path:
    """Return the path to the config overrides JSON file.

    Args:
        base_dir: Directory the overrides file lives in. Defaults to
            the current working directory.

    Returns:
        Path: Path to the overrides file (which may not yet exist).
    """
    directory = base_dir if base_dir is not None else Path.cwd()
    return directory / CONFIG_OVERRIDES_FILENAME


def _read_overrides(path: Path) -> dict[str, Any]:
    """Read the overrides JSON file, tolerating a missing file.

    Args:
        path: Path to the overrides file.

    Returns:
        dict[str, Any]: The parsed overrides, or an empty dict if the
        file does not exist.
    """
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_settings(base_dir: Path | None = None) -> Settings:
    """Load QueueCTL settings, applying persisted overrides last.

    Args:
        base_dir: Directory to look for the overrides file in.
            Defaults to the current working directory.

    Returns:
        Settings: The fully resolved settings object.
    """
    overrides = _read_overrides(get_overrides_path(base_dir))
    return Settings(**overrides)


def set_config_value(
    cli_key: str,
    raw_value: str,
    *,
    base_dir: Path | None = None,
) -> Settings:
    """Persist a single configuration override and return new settings.

    Args:
        cli_key: The hyphenated CLI key, e.g. ``"max-retries"``.
        raw_value: The raw string value supplied on the command line.
        base_dir: Directory the overrides file lives in. Defaults to
            the current working directory.

    Returns:
        Settings: The settings object reflecting the newly persisted
        value.

    Raises:
        UnknownConfigKeyError: If ``cli_key`` is not a recognized
            configuration key.
        ValueError: If ``raw_value`` cannot be coerced to the
            expected type, or fails Settings validation.
    """
    field_name = CLI_KEY_TO_FIELD.get(cli_key)
    if field_name is None:
        raise UnknownConfigKeyError(
            f"Unknown config key {cli_key!r}. Valid keys: "
            f"{', '.join(sorted(CLI_KEY_TO_FIELD))}."
        )

    field_type = _FIELD_TYPES[field_name]
    try:
        coerced_value: Any = field_type(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid value {raw_value!r} for {cli_key!r}: expected "
            f"{field_type.__name__}."
        ) from exc

    path = get_overrides_path(base_dir)
    overrides = _read_overrides(path)
    overrides[field_name] = coerced_value

    # Validate the merged overrides before persisting anything.
    settings = Settings(**overrides)

    path.write_text(
        json.dumps(overrides, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return settings
