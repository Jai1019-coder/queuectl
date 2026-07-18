"""Application logging setup for QueueCTL."""

from __future__ import annotations

import logging

from queuectl.infrastructure.logging.handlers import build_stream_handler

_ROOT_LOGGER_NAME = "queuectl"
_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure the ``queuectl`` logger hierarchy exactly once.

    Subsequent calls only adjust the log level, so it is safe to call
    this from both the CLI entry point and individual worker
    processes without installing duplicate handlers.

    Args:
        level: The logging level name (e.g. ``"DEBUG"``, ``"INFO"``).
    """
    global _configured

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(level)

    if not _configured:
        logger.addHandler(build_stream_handler())
        logger.propagate = False
        _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under the ``queuectl`` hierarchy.

    Args:
        name: Suffix identifying the caller, typically ``__name__``.

    Returns:
        logging.Logger: A logger named ``queuectl.<name>``.
    """
    if not _configured:
        configure_logging()
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
