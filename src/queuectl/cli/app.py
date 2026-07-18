"""Assembles the QueueCTL Typer application from its command modules."""

from __future__ import annotations

import typer

from queuectl.cli.callbacks import configure_root
from queuectl.cli.commands import config as config_commands
from queuectl.cli.commands import dlq as dlq_commands
from queuectl.cli.commands import enqueue as enqueue_commands
from queuectl.cli.commands import list_jobs as list_jobs_commands
from queuectl.cli.commands import scheduler as scheduler_commands
from queuectl.cli.commands import status as status_commands
from queuectl.cli.commands import worker as worker_commands


def build_app() -> typer.Typer:
    """Construct the root QueueCTL Typer application.

    Returns:
        typer.Typer: The fully-assembled CLI application, with every
        top-level command and command group registered.
    """
    app = typer.Typer(
        name="queuectl",
        help="QueueCTL: a durable CLI background job queue.",
        no_args_is_help=True,
        invoke_without_command=True,
    )

    app.callback()(configure_root)

    enqueue_commands.register(app)
    status_commands.register(app)
    list_jobs_commands.register(app)
    scheduler_commands.register(app)

    app.add_typer(worker_commands.build_worker_app(), name="worker")
    app.add_typer(dlq_commands.build_dlq_app(), name="dlq")
    app.add_typer(config_commands.build_config_app(), name="config")

    return app
