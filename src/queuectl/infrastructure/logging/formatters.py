"""Log formatters for QueueCTL."""

from __future__ import annotations

import logging


class QueueCtlFormatter(logging.Formatter):
    """Structured, single-line formatter used across QueueCTL.

    Produces lines of the form::

        2026-07-18T12:00:00+00:00 INFO worker.worker [worker=worker-1] message
    """

    def __init__(self) -> None:
        """Initialize the formatter with QueueCTL's standard layout."""
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
