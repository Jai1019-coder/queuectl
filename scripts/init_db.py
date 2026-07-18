#!/usr/bin/env python3
"""Initialize the QueueCTL SQLite database.

Creates the database file and schema if they don't already exist.
Safe to run repeatedly (uses ``CREATE TABLE IF NOT EXISTS``).

Usage:
    python scripts/init_db.py
"""

from __future__ import annotations

from queuectl.config.settings import get_settings
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import initialize_database


def main() -> None:
    """Initialize the database at the configured path."""
    settings = get_settings()
    connection = SQLiteConnection(settings.database_path)
    try:
        initialize_database(connection)
        print(f"Database initialized at {settings.database_path}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
