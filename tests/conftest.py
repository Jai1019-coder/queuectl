"""Shared pytest fixtures for QueueCTL's test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture()
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Run a test inside an isolated, empty working directory.

    QueueCTL resolves its database path, config overrides file, and
    worker PID file relative to the current working directory. This
    fixture guarantees each test gets a clean directory so tests never
    interfere with each other or with a developer's real project
    files.

    Args:
        tmp_path: Pytest's built-in temporary directory fixture.
        monkeypatch: Pytest's built-in monkeypatching fixture.

    Yields:
        Path: The isolated working directory.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MAX_RETRIES", raising=False)
    monkeypatch.delenv("BACKOFF_STRATEGY", raising=False)
    monkeypatch.delenv("BACKOFF_INITIAL_DELAY", raising=False)
    monkeypatch.delenv("BACKOFF_MULTIPLIER", raising=False)
    monkeypatch.delenv("BACKOFF_MAX_DELAY", raising=False)
    monkeypatch.delenv("WORKER_COUNT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("JOB_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("POLL_INTERVAL_SECONDS", raising=False)
    yield tmp_path
