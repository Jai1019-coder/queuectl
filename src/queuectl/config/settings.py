"""Convenience accessor for QueueCTL settings.

Most call sites should not need to know about the layered
default/.env/environment/overrides resolution performed by
:mod:`queuectl.config.loader`; they can simply call
:func:`get_settings`.
"""

from __future__ import annotations

from queuectl.config.loader import load_settings
from queuectl.config.schema import Settings


def get_settings() -> Settings:
    """Resolve and return the current QueueCTL settings.

    Returns:
        Settings: The fully resolved settings, including any
        persisted ``queuectl config set`` overrides.
    """
    return load_settings()
