"""Unit tests for SubprocessCommandExecutor."""

from __future__ import annotations

from queuectl.infrastructure.process.subprocess_executor import (
    SubprocessCommandExecutor,
)


def test_successful_command_reports_zero_exit_code() -> None:
    """A command that exits 0 should be reported as succeeded."""
    executor = SubprocessCommandExecutor()
    result = executor.run("exit 0")
    assert result.exit_code == 0
    assert result.succeeded is True
    assert result.timed_out is False


def test_failing_command_reports_nonzero_exit_code() -> None:
    """A command that exits non-zero should be reported as failed."""
    executor = SubprocessCommandExecutor()
    result = executor.run("exit 7")
    assert result.exit_code == 7
    assert result.succeeded is False


def test_command_captures_stdout() -> None:
    """Standard output should be captured verbatim."""
    executor = SubprocessCommandExecutor()
    result = executor.run("echo hello-world")
    assert "hello-world" in result.stdout


def test_invalid_command_does_not_raise() -> None:
    """An unresolvable command should produce a failed result, not raise."""
    executor = SubprocessCommandExecutor()
    result = executor.run("this-command-does-not-exist-xyz")
    assert result.succeeded is False
    assert result.exit_code != 0


def test_timeout_marks_result_as_timed_out() -> None:
    """Exceeding the timeout should be reported via timed_out."""
    executor = SubprocessCommandExecutor()
    result = executor.run("sleep 3", timeout_seconds=0.1)
    assert result.timed_out is True
    assert result.succeeded is False


def test_duration_is_measured() -> None:
    """duration_seconds should reflect roughly how long the command ran."""
    executor = SubprocessCommandExecutor()
    result = executor.run("exit 0")
    assert result.duration_seconds >= 0.0


def test_execution_result_str_contains_status() -> None:
    """The string representation should mention success/failure."""
    executor = SubprocessCommandExecutor()
    ok_result = executor.run("exit 0")
    failed_result = executor.run("exit 1")
    assert "ok" in str(ok_result)
    assert "failed" in str(failed_result)
