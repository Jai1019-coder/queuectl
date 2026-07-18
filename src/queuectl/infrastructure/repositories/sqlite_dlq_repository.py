"""
SQLite implementation of DlqRepository.
"""

from __future__ import annotations

import sqlite3

from queuectl.domain.entities.dlq_entry import DlqEntry
from queuectl.domain.value_objects.job_id import JobId
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.repositories.dlq_repository import DlqRepository


class SQLiteDlqRepository(DlqRepository):
    """
    SQLite-backed implementation of DlqRepository.
    """

    def __init__(
        self,
        connection: SQLiteConnection,
    ) -> None:
        self._connection = connection

    @property
    def _db(self) -> sqlite3.Connection:
        return self._connection.connection

    @staticmethod
    def _serialize(entry: DlqEntry) -> dict:
        return entry.to_dict()

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> DlqEntry:
        return DlqEntry.from_dict(dict(row))

    def save(
        self,
        entry: DlqEntry,
    ) -> None:

        if self.exists(entry.job_id):
            raise ValueError(
                f"DLQ entry for job {entry.job_id} already exists."
            )

        self._db.execute(
            """
            INSERT INTO dead_letter_queue (
                job_id,
                failed_at,
                reason,
                retry_count,
                error_message
            )
            VALUES (
                :job_id,
                :failed_at,
                :reason,
                :retry_count,
                :error_message
            )
            """,
            self._serialize(entry),
        )

        self._connection.commit()

    def get(
        self,
        job_id: JobId,
    ) -> DlqEntry | None:

        cursor = self._db.execute(
            """
            SELECT *
            FROM dead_letter_queue
            WHERE job_id = ?
            """,
            (str(job_id),),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._deserialize(row)

    def delete(
        self,
        job_id: JobId,
    ) -> None:

        self._db.execute(
            """
            DELETE
            FROM dead_letter_queue
            WHERE job_id = ?
            """,
            (str(job_id),),
        )

        self._connection.commit()

    def exists(
        self,
        job_id: JobId,
    ) -> bool:

        cursor = self._db.execute(
            """
            SELECT COUNT(*)
            FROM dead_letter_queue
            WHERE job_id = ?
            """,
            (str(job_id),),
        )

        return cursor.fetchone()[0] > 0

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DlqEntry]:

        query = """
            SELECT *
            FROM dead_letter_queue
            ORDER BY failed_at ASC
        """

        parameters: list[object] = []

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)

            if offset > 0:
                query += " OFFSET ?"
                parameters.append(offset)

        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            parameters.append(offset)

        cursor = self._db.execute(
            query,
            tuple(parameters),
        )

        return [
            self._deserialize(row)
            for row in cursor.fetchall()
        ]

    def count(self) -> int:

        cursor = self._db.execute(
            """
            SELECT COUNT(*)
            FROM dead_letter_queue
            """
        )

        return int(cursor.fetchone()[0])

    def clear(self) -> None:

        self._db.execute(
            """
            DELETE
            FROM dead_letter_queue
            """
        )

        self._connection.commit()

    def __len__(self) -> int:
        return self.count()

    def __contains__(
        self,
        job_id: JobId,
    ) -> bool:
        return self.exists(job_id)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(entries={self.count()})"
        )