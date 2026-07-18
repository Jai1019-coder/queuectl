"""Scripted fake CommandExecutor for unit tests."""

from __future__ import annotations

from queuectl.infrastructure.process.command_executor import CommandExecutor
from queuectl.infrastructure.process.execution_result import ExecutionResult


class FakeCommandExecutor(CommandExecutor):
    """Returns pre-scripted results instead of running real commands.

    By default every command "succeeds". Individual commands can be
    scripted to fail via :meth:`fail_on`.
    """

    def __init__(self) -> None:
        """Initialize with no failures scripted."""
        self._failures: dict[str, str] = {}
        self.calls: list[str] = []

    def fail_on(self, command: str, error_message: str = "boom") -> None:
        """Script ``command`` to fail with ``error_message``.

        Args:
            command: The exact command string to fail on.
            error_message: The stderr text the failure should carry.
        """
        self._failures[command] = error_message

    def run(
        self,
        command: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        """Return a scripted result for ``command``.

        Args:
            command: The command "executed".
            timeout_seconds: Unused; present to satisfy the interface.

        Returns:
            ExecutionResult: A failed result if ``command`` was
            scripted via :meth:`fail_on`, otherwise a successful one.
        """
        del timeout_seconds
        self.calls.append(command)

        if command in self._failures:
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr=self._failures[command],
                duration_seconds=0.0,
            )

        return ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.0,
        )
