"""`queuectl status` command."""

from __future__ import annotations

import typer

from queuectl.cli.state import cli_container
from queuectl.domain.value_objects.job_state import JobState
from queuectl.domain.value_objects.worker_status import WorkerStatus


def register(app: typer.Typer) -> None:
    """Register the ``status`` command on ``app``.

    Args:
        app: The root Typer application.
    """

    @app.command("status")
    def status() -> None:
        """Show a summary of all job states and active workers."""
        with cli_container() as container:
            typer.echo("Jobs:")
            for state in JobState:
                count = container.job_repository.count(state=state)
                typer.echo(f"  {state.value:<12} {count}")

            typer.echo("")
            typer.echo("Workers:")
            for worker_status in WorkerStatus:
                count = container.worker_repository.count(status=worker_status)
                typer.echo(f"  {worker_status.value:<12} {count}")

            typer.echo("")
            typer.echo(f"DLQ entries: {container.dlq_repository.count()}")
