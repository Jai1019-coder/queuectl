"""Unit tests for SQLiteWorkerRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.worker_status import WorkerStatus
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import initialize_database
from queuectl.infrastructure.repositories.sqlite_worker_repository import (
    SQLiteWorkerRepository,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture()
def repository() -> SQLiteWorkerRepository:
    """Provide a SQLiteWorkerRepository backed by an in-memory database."""
    connection = SQLiteConnection(":memory:")
    initialize_database(connection)
    return SQLiteWorkerRepository(connection)


def _register(worker_id: str, *, offset_seconds: int = 0, tags=None) -> Worker:
    """Build a registered worker with a deterministic started_at."""
    return Worker.register(
        worker_id=worker_id,
        hostname="test-host",
        tags=tags,
        now=BASE_TIME + timedelta(seconds=offset_seconds),
    )


class TestSaveAndGet:
    """Tests for save() and get()."""

    def test_save_then_get_round_trips(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        worker = _register("w1", tags=["region:us"])
        repository.save(worker)

        fetched = repository.get("w1")

        assert fetched is not None
        assert fetched.id == "w1"
        assert fetched.hostname == "test-host"
        assert fetched.tags == ["region:us"]

    def test_get_unknown_returns_none(self, repository: SQLiteWorkerRepository) -> None:
        assert repository.get("missing") is None

    def test_save_duplicate_raises(self, repository: SQLiteWorkerRepository) -> None:
        repository.save(_register("w1"))
        with pytest.raises(ValueError):
            repository.save(_register("w1"))

    def test_round_trip_preserves_current_job_id(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        worker = _register("w1")
        job_id = JobId.generate()
        worker.assign_job(job_id)
        repository.save(worker)

        fetched = repository.get("w1")

        assert fetched is not None
        assert fetched.current_job_id == job_id
        assert fetched.status is WorkerStatus.BUSY


class TestUpdate:
    """Tests for update()."""

    def test_update_persists_mutation(self, repository: SQLiteWorkerRepository) -> None:
        worker = _register("w1")
        repository.save(worker)

        worker.assign_job(JobId.generate())
        repository.update(worker)

        assert repository.get("w1").status is WorkerStatus.BUSY

    def test_update_unknown_worker_raises(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        with pytest.raises(ValueError):
            repository.update(_register("ghost"))


class TestDeleteAndExists:
    """Tests for delete() and exists()."""

    def test_delete_removes_worker(self, repository: SQLiteWorkerRepository) -> None:
        repository.save(_register("w1"))
        repository.delete("w1")
        assert repository.get("w1") is None

    def test_delete_unknown_does_not_raise(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        repository.delete("missing")

    def test_exists_true_and_false(self, repository: SQLiteWorkerRepository) -> None:
        repository.save(_register("w1"))
        assert repository.exists("w1") is True
        assert repository.exists("missing") is False


class TestListAndCount:
    """Tests for list(), list_available(), and count()."""

    def test_list_orders_by_started_at(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        repository.save(_register("second", offset_seconds=10))
        repository.save(_register("first", offset_seconds=0))

        result = repository.list()

        assert [w.id for w in result] == ["first", "second"]

    def test_list_filters_by_status(self, repository: SQLiteWorkerRepository) -> None:
        busy = _register("busy-worker")
        busy.assign_job(JobId.generate())
        repository.save(busy)
        repository.save(_register("online-worker", offset_seconds=1))

        result = repository.list(status=WorkerStatus.BUSY)

        assert [w.id for w in result] == ["busy-worker"]

    def test_list_respects_limit_and_offset(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        for i in range(5):
            repository.save(_register(f"w{i}", offset_seconds=i))

        result = repository.list(limit=2, offset=1)

        assert [w.id for w in result] == ["w1", "w2"]

    def test_list_offset_without_limit(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        for i in range(3):
            repository.save(_register(f"w{i}", offset_seconds=i))

        result = repository.list(offset=1)

        assert [w.id for w in result] == ["w1", "w2"]

    def test_list_available_excludes_busy(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        online = _register("online-worker")
        busy = _register("busy-worker", offset_seconds=1)
        busy.assign_job(JobId.generate())
        repository.save(online)
        repository.save(busy)

        result = repository.list_available()

        assert [w.id for w in result] == ["online-worker"]

    def test_count_all_and_filtered(self, repository: SQLiteWorkerRepository) -> None:
        busy = _register("busy-worker")
        busy.assign_job(JobId.generate())
        repository.save(busy)
        repository.save(_register("online-worker", offset_seconds=1))

        assert repository.count() == 2
        assert repository.count(status=WorkerStatus.BUSY) == 1
        assert repository.count(status=WorkerStatus.ONLINE) == 1


class TestClearAndDunder:
    """Tests for clear(), __len__, __contains__, and __repr__."""

    def test_clear_removes_all_workers(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        repository.save(_register("w1"))
        repository.clear()
        assert repository.count() == 0

    def test_len_matches_count(self, repository: SQLiteWorkerRepository) -> None:
        repository.save(_register("w1"))
        assert len(repository) == 1

    def test_contains_checks_membership(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        repository.save(_register("w1"))
        assert "w1" in repository
        assert "missing" not in repository

    def test_repr_includes_worker_count(
        self, repository: SQLiteWorkerRepository
    ) -> None:
        repository.save(_register("w1"))
        assert "workers=1" in repr(repository)
