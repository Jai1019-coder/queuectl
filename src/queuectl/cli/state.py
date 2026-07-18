"""Shared CLI helper for constructing the dependency-injection container.

Each command builds its own short-lived :class:`Container` rather
than sharing one across the whole CLI process. This keeps commands
side-effect free until they actually run (so ``--help`` never touches
the database) and guarantees the SQLite connection is always closed,
even if a command raises.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from queuectl.config.settings import get_settings
from queuectl.core.container import Container, build_container


@contextmanager
def cli_container() -> Iterator[Container]:
    """Build a Container for the duration of a single CLI command.

    Yields:
        Container: A fully-wired container using the current
        resolved settings.
    """
    container = build_container(get_settings())
    try:
        yield container
    finally:
        container.close()
