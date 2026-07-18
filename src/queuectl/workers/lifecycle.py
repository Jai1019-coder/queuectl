"""Signal-driven graceful shutdown wiring for worker processes."""

from __future__ import annotations

import signal
from types import FrameType

from queuectl.workers.shutdown import ShutdownSignal


def install_signal_handlers(shutdown_signal: ShutdownSignal) -> None:
    """Register SIGINT/SIGTERM handlers that request graceful shutdown.

    Must be called from a process's main thread. Once installed,
    receiving either signal marks ``shutdown_signal`` as requested;
    it is the caller's responsibility to check the signal between
    units of work and exit only once the current job has finished.

    Args:
        shutdown_signal: The signal to set when SIGINT/SIGTERM arrive.
    """

    def _handle(signum: int, frame: FrameType | None) -> None:
        del signum, frame
        shutdown_signal.request()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
