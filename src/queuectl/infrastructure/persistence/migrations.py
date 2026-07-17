"""
Database initialization utilities.
"""

from __future__ import annotations

from pathlib import Path

from queuectl.infrastructure.persistence.connection import SQLiteConnection


def initialize_database(
    database: str | Path,
) -> None:
    """
    Create all database tables.
    """

    schema_path = (
        Path(__file__).parent
        / "schema.sql"
    )

    schema = schema_path.read_text(
        encoding="utf-8",
    )

    with SQLiteConnection(database) as connection:
        connection.executescript(schema)