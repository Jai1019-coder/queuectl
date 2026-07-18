"""Log handler factories for QueueCTL."""

from __future__ import annotations

import logging
import sys

from queuectl.infrastructure.logging.formatters import QueueCtlFormatter


def build_stream_handler(
    stream: object | None = None,
) -> logging.Handler:
    """Build a console log handler using QueueCTL's standard format.

    Args:
        stream: The stream to write to. Defaults to ``sys.stderr``.

    Returns:
        logging.Handler: A configured stream handler.
    """
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(QueueCtlFormatter())
    return handler
