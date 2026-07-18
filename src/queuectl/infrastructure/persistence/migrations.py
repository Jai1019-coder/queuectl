"""
Database initialization utilities.
"""

from __future__ import annotations

from pathlib import Path

from queuectl.infrastructure.persistence.connection import SQLiteConnection


def initialize_database(
    connection: SQLiteConnection,
) -> None:
    """
    Initialize the SQLite database schema.

    This function executes schema.sql using an existing
    SQLiteConnection. Using the same connection is important
    when the database is ':memory:' because every in-memory
    connection represents a different database.
    """

    schema_path = Path(__file__).parent / "schema.sql"

    schema = schema_path.read_text(
        encoding="utf-8",
    )

    connection.connection.executescript(schema)
    connection.commit()
