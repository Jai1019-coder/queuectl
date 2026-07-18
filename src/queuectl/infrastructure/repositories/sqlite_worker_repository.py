"""
SQLite implementation of WorkerRepository.
"""

from __future__ import annotations

import json
import sqlite3

from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.worker_status import WorkerStatus
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.repositories.worker_repository import WorkerRepository


class SQLiteWorkerRepository(WorkerRepository):
    """
    SQLite-backed implementation of WorkerRepository.
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
    def _serialize(worker: Worker) -> dict:
        data = worker.to_dict()

        data["tags"] = json.dumps(
            data["tags"],
            separators=(",", ":"),
        )

        return data

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> Worker:
        data = dict(row)

        data["tags"] = json.loads(data["tags"])

        return Worker.from_dict(data)

    def save(
        self,
        worker: Worker,
    ) -> None:

        if self.exists(worker.id):
            raise ValueError(f"Worker '{worker.id}' already exists.")

        self._db.execute(
            """
            INSERT INTO workers (
                id,
                hostname,
                status,
                started_at,
                last_heartbeat,
                max_concurrency,
                jobs_processed,
                current_job_id,
                tags
            )
            VALUES (
                :id,
                :hostname,
                :status,
                :started_at,
                :last_heartbeat,
                :max_concurrency,
                :jobs_processed,
                :current_job_id,
                :tags
            )
            """,
            self._serialize(worker),
        )

        self._connection.commit()

    def get(
        self,
        worker_id: str,
    ) -> Worker | None:

        cursor = self._db.execute(
            """
            SELECT *
            FROM workers
            WHERE id = ?
            """,
            (worker_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._deserialize(row)

    def update(
        self,
        worker: Worker,
    ) -> None:

        cursor = self._db.execute(
            """
            UPDATE workers
            SET
                hostname=:hostname,
                status=:status,
                started_at=:started_at,
                last_heartbeat=:last_heartbeat,
                max_concurrency=:max_concurrency,
                jobs_processed=:jobs_processed,
                current_job_id=:current_job_id,
                tags=:tags
            WHERE id=:id
            """,
            self._serialize(worker),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Worker '{worker.id}' does not exist.")

        self._connection.commit()

    def delete(
        self,
        worker_id: str,
    ) -> None:

        self._db.execute(
            """
            DELETE
            FROM workers
            WHERE id = ?
            """,
            (worker_id,),
        )

        self._connection.commit()

    def exists(
        self,
        worker_id: str,
    ) -> bool:

        cursor = self._db.execute(
            """
            SELECT COUNT(*)
            FROM workers
            WHERE id = ?
            """,
            (worker_id,),
        )

        return cursor.fetchone()[0] > 0

    def list(
        self,
        *,
        status: WorkerStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Worker]:

        query = """
            SELECT *
            FROM workers
        """

        params: list[object] = []

        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY started_at ASC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

            if offset > 0:
                query += " OFFSET ?"
                params.append(offset)

        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)

        cursor = self._db.execute(
            query,
            tuple(params),
        )

        return [self._deserialize(row) for row in cursor.fetchall()]

    def list_available(self) -> list[Worker]:

        cursor = self._db.execute(
            """
            SELECT *
            FROM workers
            WHERE status = ?
            ORDER BY started_at ASC
            """,
            (WorkerStatus.ONLINE.value,),
        )

        workers = [self._deserialize(row) for row in cursor.fetchall()]

        return [worker for worker in workers if worker.is_available()]

    def count(
        self,
        *,
        status: WorkerStatus | None = None,
    ) -> int:

        if status is None:

            cursor = self._db.execute("""
                SELECT COUNT(*)
                FROM workers
                """)

        else:

            cursor = self._db.execute(
                """
                SELECT COUNT(*)
                FROM workers
                WHERE status = ?
                """,
                (status.value,),
            )

        return int(cursor.fetchone()[0])

    def clear(self) -> None:

        self._db.execute("""
            DELETE FROM workers
            """)

        self._connection.commit()

    def __len__(self) -> int:
        return self.count()

    def __contains__(
        self,
        worker_id: str,
    ) -> bool:
        return self.exists(worker_id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}" f"(workers={self.count()})"
