"""Subprocess-backed implementation of CommandExecutor."""

from __future__ import annotations

import subprocess
import time

from queuectl.infrastructure.process.command_executor import CommandExecutor
from queuectl.infrastructure.process.execution_result import ExecutionResult


class SubprocessCommandExecutor(CommandExecutor):
    """Executes job commands via the operating system shell.

    The command string stored on a job (e.g. ``"sleep 2"`` or
    ``"echo 'Hello World'"``) is passed to :func:`subprocess.run`
    with ``shell=True``, so it runs through the platform's default
    shell (``/bin/sh`` on POSIX, ``cmd.exe`` on Windows) exactly as a
    user would type it interactively.
    """

    def run(
        self,
        command: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        """Execute ``command`` in a subprocess and capture its result.

        Args:
            command: The shell command to execute.
            timeout_seconds: Maximum time to allow the command to run.
                ``None`` means no timeout.

        Returns:
            ExecutionResult: The outcome of running the command. A
            missing executable or other OS-level failure is reported
            as a non-zero exit code rather than raising, so callers
            always receive a normal result to act on.
        """
        started = time.monotonic()

        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = time.monotonic() - started
            return ExecutionResult(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started
            return ExecutionResult(
                exit_code=-1,
                stdout=(
                    (exc.stdout or b"").decode("utf-8", errors="replace")
                    if isinstance(exc.stdout, bytes)
                    else (exc.stdout or "")
                ),
                stderr=(
                    (exc.stderr or b"").decode("utf-8", errors="replace")
                    if isinstance(exc.stderr, bytes)
                    else (exc.stderr or "")
                ),
                duration_seconds=duration,
                timed_out=True,
            )
        except OSError as exc:
            duration = time.monotonic() - started
            return ExecutionResult(
                exit_code=127,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
            )
