"""
Integration tests proving JobRepository.claim_next is race-free.

These tests exercise real OS threads against both the SQLite and
in-memory repositories to demonstrate that concurrent workers can
never claim the same job twice.
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.domain.entities.job import Job
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import initialize_database
from queuectl.infrastructure.repositories.in_memory_job_repository import (
    InMemoryJobRepository,
)
from queuectl.infrastructure.repositories.sqlite_job_repository import (
    SQLiteJobRepository,
)
from queuectl.repositories.job_repository import JobRepository

JOB_COUNT = 50
WORKER_COUNT = 8


def _claim_all_concurrently(
    repository: JobRepository,
) -> list[Job]:
    """Spin up WORKER_COUNT threads racing to claim JOB_COUNT jobs.

    Args:
        repository: The repository under test, pre-populated with
            JOB_COUNT pending jobs.

    Returns:
        list[Job]: Every job successfully claimed by any thread.
    """
    claimed: list[Job] = []
    lock = threading.Lock()

    def worker(worker_id: str) -> None:
        while True:
            job = repository.claim_next(worker_id=worker_id)
            if job is None:
                return
            with lock:
                claimed.append(job)

    threads = [
        threading.Thread(target=worker, args=(f"worker-{i}",))
        for i in range(WORKER_COUNT)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return claimed


def test_sqlite_claim_next_never_claims_a_job_twice() -> None:
    """Concurrent claim_next calls against SQLite claim each job once.

    Each thread opens its own :class:`SQLiteConnection` against a
    shared on-disk database file, mirroring how real worker
    *processes* each hold an independent connection to the same
    database in production.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "claim_next.db"

        setup_connection = SQLiteConnection(db_path)
        initialize_database(setup_connection)

        enqueue = EnqueueJob(SQLiteJobRepository(setup_connection))
        for i in range(JOB_COUNT):
            enqueue.execute(name=f"job-{i}")
        setup_connection.close()

        claimed: list[Job] = []
        lock = threading.Lock()

        def worker(worker_id: str) -> None:
            connection = SQLiteConnection(db_path)
            repository = SQLiteJobRepository(connection)
            try:
                while True:
                    job = repository.claim_next(worker_id=worker_id)
                    if job is None:
                        return
                    with lock:
                        claimed.append(job)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=worker, args=(f"worker-{i}",))
            for i in range(WORKER_COUNT)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    claimed_ids = [job.id for job in claimed]

    assert len(claimed) == JOB_COUNT
    assert len(set(claimed_ids)) == JOB_COUNT


def test_in_memory_claim_next_never_claims_a_job_twice() -> None:
    """Concurrent claim_next calls against InMemory claim each job once."""
    repository = InMemoryJobRepository()
    enqueue = EnqueueJob(repository)

    for i in range(JOB_COUNT):
        enqueue.execute(name=f"job-{i}")

    claimed = _claim_all_concurrently(repository)

    claimed_ids = [job.id for job in claimed]

    assert len(claimed) == JOB_COUNT
    assert len(set(claimed_ids)) == JOB_COUNT
