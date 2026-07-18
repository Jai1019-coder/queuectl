"""Abstract interface for executing a job's shell command."""

from __future__ import annotations

from abc import ABC, abstractmethod

from queuectl.infrastructure.process.execution_result import ExecutionResult


class CommandExecutor(ABC):
    """Executes an arbitrary shell command on behalf of a worker.

    Kept as an interface so workers can be tested with a fake
    executor, and so alternative execution strategies (containerized,
    remote, sandboxed) can be introduced without touching worker code.
    """

    @abstractmethod
    def run(
        self,
        command: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        """Execute a command and return its outcome.

        Args:
            command: The shell command to execute, exactly as the
                user supplied it when enqueuing the job.
            timeout_seconds: Maximum time to allow the command to run
                before it is forcibly terminated. ``None`` means no
                timeout.

        Returns:
            ExecutionResult: The outcome of running the command.
        """
        raise NotImplementedError
