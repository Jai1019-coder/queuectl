"""Reusable sample job payloads for tests."""

from __future__ import annotations

import json
from typing import Any


def successful_job_payload(command: str = "echo hello") -> str:
    """Return a JSON payload string for a job that always succeeds.

    Args:
        command: The shell command to embed.

    Returns:
        str: A JSON-encoded job payload suitable for the ``enqueue``
        CLI command.
    """
    return json.dumps({"command": command})


def failing_job_payload(command: str = "exit 1") -> str:
    """Return a JSON payload string for a job that always fails.

    Args:
        command: The shell command to embed.

    Returns:
        str: A JSON-encoded job payload suitable for the ``enqueue``
        CLI command.
    """
    return json.dumps({"command": command})


def job_payload_with_priority(command: str, priority: int) -> str:
    """Return a JSON payload string with an explicit priority.

    Args:
        command: The shell command to embed.
        priority: The scheduling priority to embed.

    Returns:
        str: A JSON-encoded job payload suitable for the ``enqueue``
        CLI command.
    """
    return json.dumps({"command": command, "priority": priority})


def job_payload_with_extras(command: str, **extra: Any) -> str:
    """Return a JSON payload string with additional custom fields.

    Args:
        command: The shell command to embed.
        **extra: Additional keys to merge into the payload, e.g.
            ``payload={"to": "user@example.com"}``.

    Returns:
        str: A JSON-encoded job payload suitable for the ``enqueue``
        CLI command.
    """
    data: dict[str, Any] = {"command": command}
    data.update(extra)
    return json.dumps(data)
