"""Unit tests for SQLiteDlqRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from queuectl.domain.entities.dlq_entry import DlqEntry
from queuectl.domain.value_objects.job_id import JobId
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import initialize_database
from queuectl.infrastructure.repositories.sqlite_dlq_repository import (
    SQLiteDlqRepository,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture()
def repository() -> SQLiteDlqRepository:
    """Provide a SQLiteDlqRepository backed by an in-memory database."""
    connection = SQLiteConnection(":memory:")
    initialize_database(connection)
    return SQLiteDlqRepository(connection)


def _entry(*, offset_seconds: int = 0) -> DlqEntry:
    """Build a DLQ entry with a deterministic failed_at."""
    return DlqEntry.create(
        job_id=JobId.generate(),
        reason="Retry attempts exhausted.",
        retry_count=3,
        error_message="boom",
        failed_at=BASE_TIME + timedelta(seconds=offset_seconds),
    )


class TestSaveGetDelete:
    """Tests for save(), get(), delete(), and exists()."""

    def test_save_then_get_round_trips(self, repository: SQLiteDlqRepository) -> None:
        entry = _entry()
        repository.save(entry)

        fetched = repository.get(entry.job_id)

        assert fetched is not None
        assert fetched.job_id == entry.job_id
        assert fetched.reason == entry.reason
        assert fetched.error_message == entry.error_message
        assert fetched.retry_count == entry.retry_count

    def test_get_unknown_returns_none(self, repository: SQLiteDlqRepository) -> None:
        assert repository.get(JobId.generate()) is None

    def test_save_duplicate_raises(self, repository: SQLiteDlqRepository) -> None:
        entry = _entry()
        repository.save(entry)
        with pytest.raises(ValueError):
            repository.save(entry)

    def test_delete_removes_entry(self, repository: SQLiteDlqRepository) -> None:
        entry = _entry()
        repository.save(entry)
        repository.delete(entry.job_id)
        assert repository.get(entry.job_id) is None

    def test_delete_unknown_does_not_raise(
        self, repository: SQLiteDlqRepository
    ) -> None:
        repository.delete(JobId.generate())

    def test_exists_true_and_false(self, repository: SQLiteDlqRepository) -> None:
        entry = _entry()
        repository.save(entry)
        assert repository.exists(entry.job_id) is True
        assert repository.exists(JobId.generate()) is False


class TestListAndCount:
    """Tests for list() and count()."""

    def test_list_orders_by_failed_at(self, repository: SQLiteDlqRepository) -> None:
        second = _entry(offset_seconds=10)
        first = _entry(offset_seconds=0)
        repository.save(second)
        repository.save(first)

        result = repository.list()

        assert result[0].job_id == first.job_id
        assert result[1].job_id == second.job_id

    def test_list_respects_limit_and_offset(
        self, repository: SQLiteDlqRepository
    ) -> None:
        entries = [_entry(offset_seconds=i) for i in range(5)]
        for entry in entries:
            repository.save(entry)

        result = repository.list(limit=2, offset=1)

        assert [e.job_id for e in result] == [
            entries[1].job_id,
            entries[2].job_id,
        ]

    def test_list_offset_without_limit(self, repository: SQLiteDlqRepository) -> None:
        entries = [_entry(offset_seconds=i) for i in range(3)]
        for entry in entries:
            repository.save(entry)

        result = repository.list(offset=1)

        assert [e.job_id for e in result] == [
            entries[1].job_id,
            entries[2].job_id,
        ]

    def test_count_reflects_saved_entries(
        self, repository: SQLiteDlqRepository
    ) -> None:
        repository.save(_entry())
        repository.save(_entry(offset_seconds=1))
        assert repository.count() == 2


class TestClearAndDunder:
    """Tests for clear(), __len__, __contains__, and __repr__."""

    def test_clear_empties_repository(self, repository: SQLiteDlqRepository) -> None:
        repository.save(_entry())
        repository.clear()
        assert repository.count() == 0

    def test_len_matches_count(self, repository: SQLiteDlqRepository) -> None:
        repository.save(_entry())
        assert len(repository) == 1

    def test_contains_checks_membership(self, repository: SQLiteDlqRepository) -> None:
        entry = _entry()
        repository.save(entry)
        assert entry.job_id in repository
        assert JobId.generate() not in repository

    def test_repr_includes_entry_count(self, repository: SQLiteDlqRepository) -> None:
        repository.save(_entry())
        assert "entries=1" in repr(repository)
