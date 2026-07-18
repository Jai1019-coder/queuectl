"""Result of executing a job's shell command."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable outcome of running a job's command.

    Attributes:
        exit_code: The process exit code. ``0`` indicates success.
        stdout: Captured standard output, decoded as text.
        stderr: Captured standard error, decoded as text.
        duration_seconds: Wall-clock time the command took to run.
        timed_out: Whether the command was killed for exceeding its
            timeout.
    """

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        """Whether the command completed successfully.

        Returns:
            bool: ``True`` if the command exited with code ``0`` and
            did not time out.
        """
        return self.exit_code == 0 and not self.timed_out

    def __str__(self) -> str:
        """Return a short human-readable summary.

        Returns:
            str: A one-line summary of the result.
        """
        status = "ok" if self.succeeded else "failed"
        return (
            f"ExecutionResult({status}, exit_code={self.exit_code}, "
            f"duration={self.duration_seconds:.3f}s)"
        )
