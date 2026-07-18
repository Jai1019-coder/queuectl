"""`queuectl config` command group."""

from __future__ import annotations

import typer

from queuectl.config.loader import CLI_KEY_TO_FIELD, set_config_value
from queuectl.exceptions.config_exceptions import UnknownConfigKeyError


def build_config_app() -> typer.Typer:
    """Build the ``config`` sub-application.

    Returns:
        typer.Typer: A Typer app exposing ``set``.
    """
    config_app = typer.Typer(
        help="Manage QueueCTL configuration (retry, backoff, etc.)."
    )

    @config_app.command("set")
    def set_value(
        key: str = typer.Argument(
            ...,
            help="Config key. One of: " + ", ".join(sorted(CLI_KEY_TO_FIELD)),
        ),
        value: str = typer.Argument(..., help="New value for the key."),
    ) -> None:
        """Persist a configuration override."""
        try:
            settings = set_config_value(key, value)
        except (UnknownConfigKeyError, ValueError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

        field_name = CLI_KEY_TO_FIELD[key]
        typer.echo(f"{key} = {getattr(settings, field_name)}")

    return config_app
