"""`queuectl enqueue` command."""

from __future__ import annotations

import json

import typer

from queuectl.cli.state import cli_container


def register(app: typer.Typer) -> None:
    """Register the ``enqueue`` command on ``app``.

    Args:
        app: The root Typer application.
    """

    @app.command("enqueue")
    def enqueue(
        job: str = typer.Argument(
            ...,
            help=(
                "A raw shell command (e.g. 'sleep 2') or a JSON object "
                'like \'{"command":"sleep 2","priority":1}\'.'
            ),
        ),
        priority: int = typer.Option(
            0,
            "--priority",
            "-p",
            help="Scheduling priority; higher values run first.",
        ),
    ) -> None:
        """Add a new job to the queue."""
        name = job
        job_priority = priority
        payload: dict = {}

        try:
            parsed = json.loads(job)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            if "command" not in parsed:
                typer.secho(
                    "JSON job payload must include a 'command' field.",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)
            name = parsed["command"]
            job_priority = int(parsed.get("priority", priority))
            payload = parsed.get("payload", {})

        with cli_container() as container:
            created = container.enqueue_job.execute(
                name=name,
                payload=payload,
                priority=job_priority,
            )
            typer.echo(json.dumps(created.to_dict(), indent=2))
