"""Unit tests for InMemoryWorkerRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.worker_status import WorkerStatus
from queuectl.infrastructure.repositories.in_memory_worker_repository import (
    InMemoryWorkerRepository,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _register(worker_id: str, *, offset_seconds: int = 0) -> Worker:
    """Build a registered worker with a deterministic started_at."""
    return Worker.register(
        worker_id=worker_id,
        hostname="test-host",
        now=BASE_TIME + timedelta(seconds=offset_seconds),
    )


class TestSaveAndGet:
    """Tests for save() and get()."""

    def test_save_then_get_returns_worker(self) -> None:
        repository = InMemoryWorkerRepository()
        worker = _register("w1")
        repository.save(worker)
        assert repository.get("w1") is worker

    def test_get_unknown_worker_returns_none(self) -> None:
        repository = InMemoryWorkerRepository()
        assert repository.get("missing") is None

    def test_save_duplicate_id_raises(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        with pytest.raises(ValueError):
            repository.save(_register("w1"))


class TestUpdate:
    """Tests for update()."""

    def test_update_persists_mutation(self) -> None:
        repository = InMemoryWorkerRepository()
        worker = _register("w1")
        repository.save(worker)

        worker.assign_job(JobId.generate())
        repository.update(worker)

        assert repository.get("w1").status is WorkerStatus.BUSY

    def test_update_unknown_worker_raises(self) -> None:
        repository = InMemoryWorkerRepository()
        with pytest.raises(ValueError):
            repository.update(_register("ghost"))


class TestDeleteAndExists:
    """Tests for delete() and exists()."""

    def test_delete_removes_worker(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        repository.delete("w1")
        assert repository.get("w1") is None

    def test_delete_unknown_worker_does_not_raise(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.delete("missing")

    def test_exists_true_for_saved_worker(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        assert repository.exists("w1") is True

    def test_exists_false_for_unknown_worker(self) -> None:
        repository = InMemoryWorkerRepository()
        assert repository.exists("missing") is False


class TestList:
    """Tests for list()."""

    def test_list_orders_by_registration_time(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("second", offset_seconds=10))
        repository.save(_register("first", offset_seconds=0))

        result = repository.list()

        assert [w.id for w in result] == ["first", "second"]

    def test_list_filters_by_status(self) -> None:
        repository = InMemoryWorkerRepository()
        online = _register("online-worker")
        busy = _register("busy-worker", offset_seconds=1)
        busy.assign_job(JobId.generate())
        repository.save(online)
        repository.save(busy)

        result = repository.list(status=WorkerStatus.BUSY)

        assert [w.id for w in result] == ["busy-worker"]

    def test_list_respects_limit_and_offset(self) -> None:
        repository = InMemoryWorkerRepository()
        for i in range(5):
            repository.save(_register(f"w{i}", offset_seconds=i))

        result = repository.list(limit=2, offset=1)

        assert [w.id for w in result] == ["w1", "w2"]


class TestListAvailable:
    """Tests for list_available()."""

    def test_list_available_excludes_busy_and_offline(self) -> None:
        repository = InMemoryWorkerRepository()
        online = _register("online-worker")
        busy = _register("busy-worker", offset_seconds=1)
        busy.assign_job(JobId.generate())
        offline = _register("offline-worker", offset_seconds=2)
        offline.set_offline()

        repository.save(online)
        repository.save(busy)
        repository.save(offline)

        result = repository.list_available()

        assert [w.id for w in result] == ["online-worker"]


class TestCount:
    """Tests for count()."""

    def test_count_all_workers(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        repository.save(_register("w2", offset_seconds=1))
        assert repository.count() == 2

    def test_count_filtered_by_status(self) -> None:
        repository = InMemoryWorkerRepository()
        busy = _register("w1")
        busy.assign_job(JobId.generate())
        repository.save(busy)
        repository.save(_register("w2", offset_seconds=1))

        assert repository.count(status=WorkerStatus.BUSY) == 1
        assert repository.count(status=WorkerStatus.ONLINE) == 1


class TestClearAndDunder:
    """Tests for clear(), __len__, __contains__, and __repr__."""

    def test_clear_removes_all_workers(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        repository.clear()
        assert repository.count() == 0

    def test_len_reflects_worker_count(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        repository.save(_register("w2", offset_seconds=1))
        assert len(repository) == 2

    def test_contains_checks_membership(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        assert "w1" in repository
        assert "missing" not in repository

    def test_repr_includes_worker_count(self) -> None:
        repository = InMemoryWorkerRepository()
        repository.save(_register("w1"))
        assert "workers=1" in repr(repository)
