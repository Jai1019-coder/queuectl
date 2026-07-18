"""Unit tests for InMemoryJobRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.repositories.in_memory_job_repository import (
    InMemoryJobRepository,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _job(name: str = "echo hi", *, offset_seconds: int = 0, priority: int = 0) -> Job:
    """Build a job with a deterministic created_at."""
    return Job.create(
        name=name,
        priority=priority,
        now=BASE_TIME + timedelta(seconds=offset_seconds),
    )


class TestSaveAndGet:
    """Tests for save() and get()."""

    def test_save_then_get_round_trips(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)
        assert repository.get(job.id) is job

    def test_get_unknown_returns_none(self) -> None:
        repository = InMemoryJobRepository()
        assert repository.get(JobId.generate()) is None

    def test_save_duplicate_raises(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)
        with pytest.raises(ValueError):
            repository.save(job)


class TestUpdate:
    """Tests for update()."""

    def test_update_persists_mutation(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)

        job.claim("worker-1", now=BASE_TIME)
        repository.update(job)

        assert repository.get(job.id).state is JobState.PROCESSING

    def test_update_unknown_job_raises(self) -> None:
        repository = InMemoryJobRepository()
        with pytest.raises(ValueError):
            repository.update(_job())


class TestDeleteAndExists:
    """Tests for delete() and exists()."""

    def test_delete_removes_job(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)
        repository.delete(job.id)
        assert repository.get(job.id) is None

    def test_delete_unknown_does_not_raise(self) -> None:
        repository = InMemoryJobRepository()
        repository.delete(JobId.generate())

    def test_exists_true_and_false(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)
        assert repository.exists(job.id) is True
        assert repository.exists(JobId.generate()) is False


class TestList:
    """Tests for list()."""

    def test_list_orders_by_created_at(self) -> None:
        repository = InMemoryJobRepository()
        second = _job("second", offset_seconds=10)
        first = _job("first", offset_seconds=0)
        repository.save(second)
        repository.save(first)

        result = repository.list()

        assert [job.name for job in result] == ["first", "second"]

    def test_list_filters_by_state(self) -> None:
        repository = InMemoryJobRepository()
        pending = _job("pending-job")
        processing = _job("processing-job", offset_seconds=1)
        processing.claim("worker-1", now=BASE_TIME + timedelta(seconds=1))
        repository.save(pending)
        repository.save(processing)

        result = repository.list(state=JobState.PROCESSING)

        assert [job.name for job in result] == ["processing-job"]

    def test_list_respects_limit_and_offset(self) -> None:
        repository = InMemoryJobRepository()
        for i in range(5):
            repository.save(_job(f"job-{i}", offset_seconds=i))

        result = repository.list(limit=2, offset=1)

        assert [job.name for job in result] == ["job-1", "job-2"]


class TestNextAvailable:
    """Tests for next_available()."""

    def test_returns_none_when_empty(self) -> None:
        repository = InMemoryJobRepository()
        assert repository.next_available() is None

    def test_prefers_higher_priority(self) -> None:
        repository = InMemoryJobRepository()
        low = _job("low", priority=0)
        high = _job("high", priority=5, offset_seconds=1)
        repository.save(low)
        repository.save(high)

        assert repository.next_available().name == "high"

    def test_prefers_earlier_created_at_on_tie(self) -> None:
        repository = InMemoryJobRepository()
        second = _job("second", offset_seconds=10)
        first = _job("first", offset_seconds=0)
        repository.save(second)
        repository.save(first)

        assert repository.next_available().name == "first"

    def test_excludes_not_yet_available_jobs(self) -> None:
        repository = InMemoryJobRepository()
        job = _job("delayed")
        job.available_at = datetime.now(UTC) + timedelta(hours=1)
        repository.save(job)

        assert repository.next_available() is None


class TestClaimNext:
    """Tests for claim_next()."""

    def test_claims_and_transitions_to_processing(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)

        claimed = repository.claim_next("worker-1")

        assert claimed is not None
        assert claimed.state is JobState.PROCESSING
        assert claimed.worker_id == "worker-1"

    def test_returns_none_when_no_job_available(self) -> None:
        repository = InMemoryJobRepository()
        assert repository.claim_next("worker-1") is None

    def test_rejects_empty_worker_id(self) -> None:
        repository = InMemoryJobRepository()
        repository.save(_job())
        with pytest.raises(ValueError):
            repository.claim_next("")


class TestCount:
    """Tests for count()."""

    def test_count_all_jobs(self) -> None:
        repository = InMemoryJobRepository()
        repository.save(_job("a"))
        repository.save(_job("b", offset_seconds=1))
        assert repository.count() == 2

    def test_count_filtered_by_state(self) -> None:
        repository = InMemoryJobRepository()
        processing = _job("a")
        processing.claim("worker-1", now=BASE_TIME)
        repository.save(processing)
        repository.save(_job("b", offset_seconds=1))

        assert repository.count(state=JobState.PROCESSING) == 1
        assert repository.count(state=JobState.PENDING) == 1


class TestClearAndDunder:
    """Tests for clear(), __len__, __contains__, and __repr__."""

    def test_clear_removes_all_jobs(self) -> None:
        repository = InMemoryJobRepository()
        repository.save(_job())
        repository.clear()
        assert repository.count() == 0

    def test_len_matches_count(self) -> None:
        repository = InMemoryJobRepository()
        repository.save(_job())
        assert len(repository) == 1

    def test_contains_checks_membership(self) -> None:
        repository = InMemoryJobRepository()
        job = _job()
        repository.save(job)
        assert job.id in repository
        assert JobId.generate() not in repository

    def test_repr_includes_job_count(self) -> None:
        repository = InMemoryJobRepository()
        repository.save(_job())
        assert "jobs=1" in repr(repository)
