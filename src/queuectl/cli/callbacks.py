"""Root Typer callback: logging setup and bare-invocation help."""

from __future__ import annotations

import typer

from queuectl.config.settings import get_settings
from queuectl.infrastructure.logging.logger import configure_logging


def configure_root(ctx: typer.Context) -> None:
    """Configure logging and show help when no subcommand is given.

    Args:
        ctx: The active Typer/Click context.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
