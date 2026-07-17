"""
SQLite database connection manager.

Provides a single place to create, configure and manage SQLite
connections used throughout the persistence layer.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteConnection:
    """
    Manages a SQLite database connection.

    Responsibilities
    ----------------
    - Open database connections
    - Enable SQLite foreign key constraints
    - Return rows as sqlite3.Row objects
    - Close connections cleanly
    """

    def __init__(self, database: str | Path) -> None:
        self._database = str(database)
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        """
        Return an active SQLite connection.

        The connection is created lazily on first access.
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._database,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )

            self._connection.row_factory = sqlite3.Row

            self._connection.execute(
                "PRAGMA foreign_keys = ON;"
            )

        return self._connection

    def cursor(self) -> sqlite3.Cursor:
        """
        Return a cursor from the active connection.
        """
        return self.connection.cursor()

    def commit(self) -> None:
        """
        Commit the current transaction.
        """
        self.connection.commit()

    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """
        self.connection.rollback()

    def close(self) -> None:
        """
        Close the database connection.
        """
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> sqlite3.Connection:
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

        self.close()