"""`queuectl list` command."""

from __future__ import annotations

import typer

from queuectl.cli.state import cli_container
from queuectl.domain.value_objects.job_state import JobState


def register(app: typer.Typer) -> None:
    """Register the ``list`` command on ``app``.

    Args:
        app: The root Typer application.
    """

    @app.command("list")
    def list_jobs(
        state: str | None = typer.Option(
            None,
            "--state",
            help="Filter by job state: pending, processing, completed, "
            "failed, or dead.",
        ),
        limit: int = typer.Option(
            50, "--limit", help="Maximum number of jobs to show."
        ),
    ) -> None:
        """List jobs, optionally filtered by state."""
        job_state: JobState | None = None

        if state is not None:
            try:
                job_state = JobState(state.lower())
            except ValueError:
                valid = ", ".join(s.value for s in JobState)
                typer.secho(
                    f"Invalid state {state!r}. Valid states: {valid}.",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1) from None

        with cli_container() as container:
            jobs = container.job_repository.list(state=job_state, limit=limit)

            if not jobs:
                typer.echo("No jobs found.")
                return

            for job in jobs:
                typer.echo(
                    f"{job.id}  {job.state.value:<10}  "
                    f"priority={job.priority:<3}  "
                    f"retries={job.retry_count:<2}  {job.name}"
                )
