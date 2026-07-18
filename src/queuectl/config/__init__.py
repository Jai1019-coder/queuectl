"""Configuration management for QueueCTL."""

from __future__ import annotations

from queuectl.config.schema import Settings
from queuectl.config.settings import get_settings

__all__ = ["Settings", "get_settings"]
