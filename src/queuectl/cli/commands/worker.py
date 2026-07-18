"""`queuectl worker` command group."""

from __future__ import annotations

import typer

from queuectl.config.settings import get_settings
from queuectl.workers.worker_manager import start_workers, stop_workers


def build_worker_app() -> typer.Typer:
    """Build the ``worker`` sub-application.

    Returns:
        typer.Typer: A Typer app exposing ``start`` and ``stop``.
    """
    worker_app = typer.Typer(help="Start and stop QueueCTL worker processes.")

    @worker_app.command("start")
    def start(
        count: int | None = typer.Option(
            None,
            "--count",
            "-c",
            help="Number of worker processes to start. Defaults to the "
            "configured worker_count.",
        ),
        drain: bool = typer.Option(
            False,
            "--drain/--no-drain",
            help="Process every currently-queued job and exit, instead "
            "of running indefinitely.",
        ),
    ) -> None:
        """Start one or more workers.

        By default, blocks in the foreground, processing jobs until
        interrupted with Ctrl+C or stopped from another terminal via
        ``queuectl worker stop``. With ``--drain``, each worker exits
        as soon as the queue is empty.
        """
        settings = get_settings()
        worker_count = count or settings.worker_count

        if drain:
            typer.echo(f"Draining the queue with {worker_count} worker(s)...")
        else:
            typer.echo(
                f"Starting {worker_count} worker(s). Press Ctrl+C or run "
                "'queuectl worker stop' from another terminal to stop."
            )

        start_workers(settings, count=worker_count, block=True, drain=drain)

        typer.echo("All workers stopped.")

    @worker_app.command("stop")
    def stop() -> None:
        """Stop running workers gracefully.

        Finishes any job a worker is currently executing before that
        worker exits.
        """
        stopped = stop_workers()

        if stopped == 0:
            typer.echo("No running workers found.")
        else:
            typer.echo(f"Stopped {stopped} worker(s).")

    return worker_app
