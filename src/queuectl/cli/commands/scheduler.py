"""`queuectl scheduler` command.

Lists jobs currently sitting in the PENDING state with a future
``available_at`` timestamp -- i.e. jobs waiting out a retry backoff
delay before they become claimable again. This is a lightweight,
read-only view built directly on top of existing job persistence;
full delayed-job scheduling (arbitrary ``run_at`` on initial enqueue)
is a bonus feature not required by the core specification.
"""

from __future__ import annotations

import typer

from queuectl.cli.state import cli_container
from queuectl.core.interfaces import SystemClock
from queuectl.domain.value_objects.job_state import JobState


def register(app: typer.Typer) -> None:
    """Register the ``scheduler`` command on ``app``.

    Args:
        app: The root Typer application.
    """

    @app.command("scheduler")
    def scheduler() -> None:
        """List jobs currently waiting out a retry backoff delay."""
        now = SystemClock().now()

        with cli_container() as container:
            pending_jobs = container.job_repository.list(state=JobState.PENDING)
            delayed = [job for job in pending_jobs if job.available_at > now]

            if not delayed:
                typer.echo("No delayed jobs scheduled.")
                return

            for job in sorted(delayed, key=lambda candidate: candidate.available_at):
                wait_seconds = (job.available_at - now).total_seconds()
                typer.echo(
                    f"{job.id}  retries={job.retry_count}  "
                    f"available_in={wait_seconds:.1f}s  {job.name}"
                )
