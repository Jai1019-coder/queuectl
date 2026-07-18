"""`queuectl dlq` command group."""

from __future__ import annotations

import typer

from queuectl.cli.state import cli_container
from queuectl.domain.value_objects.job_id import JobId


def build_dlq_app() -> typer.Typer:
    """Build the ``dlq`` sub-application.

    Returns:
        typer.Typer: A Typer app exposing ``list`` and ``retry``.
    """
    dlq_app = typer.Typer(help="Inspect and replay Dead Letter Queue entries.")

    @dlq_app.command("list")
    def list_entries() -> None:
        """View jobs currently in the Dead Letter Queue."""
        with cli_container() as container:
            entries = container.dlq_repository.list()

            if not entries:
                typer.echo("DLQ is empty.")
                return

            for entry in entries:
                typer.echo(
                    f"{entry.job_id}  retries={entry.retry_count}  "
                    f"reason={entry.reason!r}  "
                    f"error={entry.error_message!r}"
                )

    @dlq_app.command("retry")
    def retry(
        job_id: str = typer.Argument(..., help="ID of the job to replay from the DLQ."),
    ) -> None:
        """Replay a job from the Dead Letter Queue back to PENDING."""
        try:
            parsed_id = JobId.from_string(job_id)
        except ValueError:
            typer.secho(f"Invalid job id {job_id!r}.", fg=typer.colors.RED)
            raise typer.Exit(code=1) from None

        with cli_container() as container:
            try:
                job = container.replay_dlq_job.execute(job_id=parsed_id)
            except ValueError as exc:
                typer.secho(str(exc), fg=typer.colors.RED)
                raise typer.Exit(code=1) from exc

            typer.echo(f"Job {job.id} reset to {job.state.value} and ready for retry.")

    return dlq_app
