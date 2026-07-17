"""Command-line entry point for QueueCTL."""

import typer

app = typer.Typer(
    help="QueueCTL command line interface.",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def root(ctx: typer.Context) -> None:
    """Show placeholder help until CLI commands are implemented."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
