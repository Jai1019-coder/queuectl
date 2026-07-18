"""Shutdown signaling primitive shared by worker runtimes."""

from __future__ import annotations

import threading


class ShutdownSignal:
    """A simple, thread-safe flag requesting graceful shutdown.

    Wraps a :class:`threading.Event` so worker loops can poll for a
    shutdown request between jobs without needing to know whether the
    request originated from an OS signal, a parent process, or a
    test.
    """

    def __init__(self) -> None:
        """Initialize the signal in the "not requested" state."""
        self._event = threading.Event()

    def request(self) -> None:
        """Request a graceful shutdown."""
        self._event.set()

    def is_set(self) -> bool:
        """Return whether shutdown has been requested.

        Returns:
            bool: True if :meth:`request` has been called.
        """
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until shutdown is requested or the timeout elapses.

        Args:
            timeout: Maximum time to wait, in seconds. ``None`` waits
                indefinitely.

        Returns:
            bool: True if shutdown was requested before the timeout.
        """
        return self._event.wait(timeout)
