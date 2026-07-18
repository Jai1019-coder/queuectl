"""Command-line entry point for QueueCTL."""

from __future__ import annotations

from queuectl.cli.app import build_app

app = build_app()

if __name__ == "__main__":
    app()
