"""
SQLite implementation of JobRepository.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.repositories.job_repository import JobRepository


class SQLiteJobRepository(JobRepository):
    """
    SQLite-backed implementation of JobRepository.
    """

    def __init__(
        self,
        connection: SQLiteConnection,
    ) -> None:
        """
        Initialize the repository.

        Args:
            connection:
                SQLite connection wrapper.
        """
        self._connection = connection

    @property
    def _db(self) -> sqlite3.Connection:
        """
        Return the active SQLite connection.
        """
        return self._connection.connection

    # ------------------------------------------------------------------
    # Serialization Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(job: Job) -> dict[str, Any]:
        """
        Convert a Job into a dictionary suitable for SQLite.

        Datetimes are already serialized by Job.to_dict().
        Only the payload needs JSON encoding.
        """
        data = job.to_dict()

        data["payload"] = json.dumps(
            data["payload"],
            separators=(",", ":"),
        )

        return data

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> Job:
        """
        Convert a SQLite row back into a Job entity.
        """

        data = dict(row)

        data["payload"] = json.loads(data["payload"])

        return Job.from_dict(data)

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    def save(
        self,
        job: Job,
    ) -> None:
        """
        Persist a new Job.

        Raises:
            ValueError:
                If the job already exists.
        """

        if self.exists(job.id):
            raise ValueError(f"Job {job.id} already exists.")

        data = self._serialize(job)

        self._db.execute(
            """
            INSERT INTO jobs (
                id,
                name,
                payload,
                priority,
                state,
                retry_count,
                created_at,
                updated_at,
                available_at,
                started_at,
                completed_at,
                worker_id,
                error_message
            )
            VALUES (
                :id,
                :name,
                :payload,
                :priority,
                :state,
                :retry_count,
                :created_at,
                :updated_at,
                :available_at,
                :started_at,
                :completed_at,
                :worker_id,
                :error_message
            )
            """,
            data,
        )

        self._db.commit()

    def get(
        self,
        job_id: JobId,
    ) -> Job | None:
        """
        Retrieve a job by its identifier.
        """

        cursor = self._db.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = ?
            """,
            (str(job_id),),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._deserialize(row)

    def update(
        self,
        job: Job,
    ) -> None:
        """
        Persist changes made to an existing job.

        Raises:
            ValueError:
                If the job does not exist.
        """

        data = self._serialize(job)

        cursor = self._db.execute(
            """
            UPDATE jobs
            SET
                name = :name,
                payload = :payload,
                priority = :priority,
                state = :state,
                retry_count = :retry_count,
                created_at = :created_at,
                updated_at = :updated_at,
                available_at = :available_at,
                started_at = :started_at,
                completed_at = :completed_at,
                worker_id = :worker_id,
                error_message = :error_message
            WHERE id = :id
            """,
            data,
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Job {job.id} does not exist.")

        self._db.commit()

    def delete(
        self,
        job_id: JobId,
    ) -> None:
        """
        Delete a job.

        Does nothing if the job does not exist.
        """

        self._db.execute(
            """
            DELETE
            FROM jobs
            WHERE id = ?
            """,
            (str(job_id),),
        )

        self._db.commit()

    def exists(
        self,
        job_id: JobId,
    ) -> bool:
        """
        Determine whether a job exists.
        """

        cursor = self._db.execute(
            """
            SELECT COUNT(*)
            FROM jobs
            WHERE id = ?
            """,
            (str(job_id),),
        )

        return cursor.fetchone()[0] > 0

    def list(
        self,
        *,
        state: JobState | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Job]:
        """
        List jobs ordered by creation time.
        """

        query = """
            SELECT *
            FROM jobs
        """

        parameters: list[object] = []

        if state is not None:
            query += " WHERE state = ?"
            parameters.append(state.value)

        query += " ORDER BY created_at ASC"

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

        return [self._deserialize(row) for row in cursor.fetchall()]

    def next_available(self) -> Job | None:
        """
        Return the highest-priority schedulable job.

        Ordering:
            1. Higher priority
            2. Earlier creation time
        """

        cursor = self._db.execute(
            """
            SELECT *
            FROM jobs
            WHERE state = ?
            ORDER BY
                priority DESC,
                created_at ASC
            """,
            (JobState.PENDING.value,),
        )

        for row in cursor.fetchall():

            job = self._deserialize(row)

            if job.can_be_claimed():
                return job

        return None

    def claim_next(
        self,
        worker_id: str,
        *,
        now: datetime | None = None,
    ) -> Job | None:
        """
        Atomically claim the next available job.

        A ``BEGIN IMMEDIATE`` transaction is used to acquire SQLite's
        write lock before selecting a candidate row, which serializes
        this method against every other writer (including concurrent
        ``claim_next`` calls from other worker processes). The
        candidate is claimed with a single conditional ``UPDATE ...
        WHERE state = 'pending'`` so a job can never be handed to more
        than one caller, even under heavy contention.

        Args:
            worker_id:
                Identifier of the worker claiming the job.

            now:
                Reference timestamp for availability and claim
                stamping. Defaults to the current UTC time.

        Returns:
            The claimed job, or None if no job is currently available.

        Raises:
            ValueError:
                If ``worker_id`` is empty.
        """

        if not worker_id:
            raise ValueError("worker_id must not be empty.")

        reference = (now or datetime.now(UTC)).isoformat()

        self._db.execute("BEGIN IMMEDIATE")

        try:
            candidate = self._db.execute(
                """
                SELECT id
                FROM jobs
                WHERE state = ? AND available_at <= ?
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """,
                (JobState.PENDING.value, reference),
            ).fetchone()

            if candidate is None:
                self._db.commit()
                return None

            job_id = candidate["id"]

            cursor = self._db.execute(
                """
                UPDATE jobs
                SET
                    state = ?,
                    worker_id = ?,
                    started_at = ?,
                    updated_at = ?,
                    error_message = NULL
                WHERE id = ? AND state = ?
                """,
                (
                    JobState.PROCESSING.value,
                    worker_id,
                    reference,
                    reference,
                    job_id,
                    JobState.PENDING.value,
                ),
            )

            if cursor.rowcount == 0:
                self._db.commit()
                return None

            row = self._db.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        return self._deserialize(row)

    def count(
        self,
        *,
        state: JobState | None = None,
    ) -> int:
        """
        Count jobs.
        """

        if state is None:

            cursor = self._db.execute("""
                SELECT COUNT(*)
                FROM jobs
                """)

        else:

            cursor = self._db.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE state = ?
                """,
                (state.value,),
            )

        return int(cursor.fetchone()[0])

    def clear(self) -> None:
        """
        Remove every job.
        """

        self._db.execute("""
            DELETE FROM jobs
            """)

        self._db.commit()

    def __len__(self) -> int:
        return self.count()

    def __contains__(
        self,
        job_id: JobId,
    ) -> bool:
        return self.exists(job_id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}" f"(jobs={self.count()})"
