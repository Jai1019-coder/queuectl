"""Smoke tests for the Phase 0 project skeleton."""

from queuectl.main import app


def test_typer_app_is_importable() -> None:
    """Confirm the placeholder CLI app imports."""
    assert app is not None
