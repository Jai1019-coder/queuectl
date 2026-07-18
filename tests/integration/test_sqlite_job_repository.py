"""
Tests for SQLiteJobRepository.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from queuectl.domain.entities.job import Job
from queuectl.domain.entities.worker import Worker
from queuectl.domain.value_objects.job_state import JobState
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import (
    initialize_database,
)
from queuectl.infrastructure.repositories.sqlite_job_repository import (
    SQLiteJobRepository,
)
from queuectl.infrastructure.repositories.sqlite_worker_repository import (
    SQLiteWorkerRepository,
)

now = datetime.now(UTC)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def connection() -> SQLiteConnection:
    """
    Create an in-memory SQLite database.
    """

    connection = SQLiteConnection(":memory:")
    initialize_database(connection)
    return connection


@pytest.fixture
def repository(
    connection: SQLiteConnection,
) -> SQLiteJobRepository:
    """
    Repository under test.
    """

    return SQLiteJobRepository(connection)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def utc(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        tzinfo=UTC,
    )


def create_job(
    *,
    name: str = "email",
    priority: int = 0,
    now: datetime | None = None,
) -> Job:

    timestamp = now or utc(2025, 1, 1)

    return Job.create(
        name=name,
        priority=priority,
        now=timestamp,
    )


# ----------------------------------------------------------------------
# Save / Get
# ----------------------------------------------------------------------


def test_save_and_get_job(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.id == job.id
    assert loaded.name == job.name
    assert loaded.priority == job.priority
    assert loaded.state == JobState.PENDING
    assert loaded.payload == {}


# ----------------------------------------------------------------------
# Duplicate Save
# ----------------------------------------------------------------------


def test_save_duplicate_job_raises_error(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    with pytest.raises(ValueError):
        repository.save(job)


# ----------------------------------------------------------------------
# Exists
# ----------------------------------------------------------------------


def test_exists_returns_true_for_saved_job(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    assert repository.exists(job.id)


def test_exists_returns_false_for_unknown_job(
    repository: SQLiteJobRepository,
):

    job = create_job()

    assert repository.exists(job.id) is False


# ----------------------------------------------------------------------
# Delete
# ----------------------------------------------------------------------


def test_delete_existing_job(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    repository.delete(job.id)

    assert repository.get(job.id) is None
    assert repository.exists(job.id) is False


def test_delete_missing_job_is_noop(
    repository: SQLiteJobRepository,
):

    job = create_job()

    # Should not raise.
    repository.delete(job.id)

    assert repository.count() == 0


# ----------------------------------------------------------------------
# Update
# ----------------------------------------------------------------------


def test_update_existing_job(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    job.priority = 10
    job.payload["email"] = "alice@example.com"

    repository.update(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.priority == 10
    assert loaded.payload == {
        "email": "alice@example.com",
    }


def test_update_missing_job_raises_error(
    repository: SQLiteJobRepository,
):

    job = create_job()

    with pytest.raises(ValueError):
        repository.update(job)


# ----------------------------------------------------------------------
# Count
# ----------------------------------------------------------------------


def test_count_empty_repository(
    repository: SQLiteJobRepository,
):

    assert repository.count() == 0


def test_count_after_multiple_saves(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())
    repository.save(create_job(name="resize"))
    repository.save(create_job(name="backup"))

    assert repository.count() == 3


def test_count_by_state(
    repository: SQLiteJobRepository,
):

    first = create_job(name="A")
    second = create_job(name="B")

    repository.save(first)
    repository.save(second)

    second.mark_processing()

    repository.update(second)

    assert (
        repository.count(
            state=JobState.PENDING,
        )
        == 1
    )

    assert (
        repository.count(
            state=JobState.PROCESSING,
        )
        == 1
    )


# ----------------------------------------------------------------------
# Clear
# ----------------------------------------------------------------------


def test_clear_repository(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())
    repository.save(create_job(name="resize"))

    assert repository.count() == 2

    repository.clear()

    assert repository.count() == 0


# ----------------------------------------------------------------------
# Magic Methods
# ----------------------------------------------------------------------


def test_len_returns_job_count(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())
    repository.save(create_job(name="cleanup"))

    assert len(repository) == 2


def test_contains_operator(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    assert job.id in repository

    repository.delete(job.id)

    assert job.id not in repository


# ----------------------------------------------------------------------
# List
# ----------------------------------------------------------------------


def test_list_empty_repository(
    repository: SQLiteJobRepository,
):

    assert repository.list() == []


def test_list_returns_jobs_ordered_by_creation_time(
    repository: SQLiteJobRepository,
):

    first = create_job(
        name="first",
        now=utc(2025, 1, 1, 10),
    )

    second = create_job(
        name="second",
        now=utc(2025, 1, 1, 11),
    )

    third = create_job(
        name="third",
        now=utc(2025, 1, 1, 12),
    )

    repository.save(second)
    repository.save(third)
    repository.save(first)

    jobs = repository.list()

    assert [job.name for job in jobs] == [
        "first",
        "second",
        "third",
    ]


def test_list_filters_by_state(
    repository: SQLiteJobRepository,
):

    pending = create_job(name="pending")

    processing = create_job(name="processing")

    completed = create_job(name="completed")

    repository.save(pending)
    repository.save(processing)
    repository.save(completed)

    processing.mark_processing()
    repository.update(processing)

    completed.mark_processing()
    completed.mark_completed()
    repository.update(completed)

    pending_jobs = repository.list(
        state=JobState.PENDING,
    )

    processing_jobs = repository.list(
        state=JobState.PROCESSING,
    )

    completed_jobs = repository.list(
        state=JobState.COMPLETED,
    )

    assert len(pending_jobs) == 1
    assert pending_jobs[0].name == "pending"

    assert len(processing_jobs) == 1
    assert processing_jobs[0].name == "processing"

    assert len(completed_jobs) == 1
    assert completed_jobs[0].name == "completed"


def test_list_with_limit(
    repository: SQLiteJobRepository,
):

    for i in range(5):
        repository.save(
            create_job(
                name=f"job-{i}",
                now=utc(2025, 1, 1, i),
            )
        )

    jobs = repository.list(limit=2)

    assert len(jobs) == 2

    assert jobs[0].name == "job-0"
    assert jobs[1].name == "job-1"


def test_list_with_offset(
    repository: SQLiteJobRepository,
):

    for i in range(5):
        repository.save(
            create_job(
                name=f"job-{i}",
                now=utc(2025, 1, 1, i),
            )
        )

    jobs = repository.list(offset=2)

    assert len(jobs) == 3

    assert [job.name for job in jobs] == [
        "job-2",
        "job-3",
        "job-4",
    ]


def test_list_with_limit_and_offset(
    repository: SQLiteJobRepository,
):

    for i in range(6):
        repository.save(
            create_job(
                name=f"job-{i}",
                now=utc(2025, 1, 1, i),
            )
        )

    jobs = repository.list(
        limit=2,
        offset=3,
    )

    assert len(jobs) == 2

    assert [job.name for job in jobs] == [
        "job-3",
        "job-4",
    ]


def test_list_state_filter_with_limit(
    repository: SQLiteJobRepository,
):

    for i in range(5):

        job = create_job(
            name=f"job-{i}",
            now=utc(2025, 1, 1, i),
        )

        repository.save(job)

        if i % 2 == 0:
            job.mark_processing()
            repository.update(job)

    processing = repository.list(
        state=JobState.PROCESSING,
        limit=2,
    )

    assert len(processing) == 2

    assert all(job.state == JobState.PROCESSING for job in processing)


def test_list_returns_new_objects(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    first = repository.list()

    second = repository.list()

    assert first is not second

    assert first[0] == second[0]


# ----------------------------------------------------------------------
# next_available()
# ----------------------------------------------------------------------


def test_next_available_returns_none_when_repository_empty(
    repository: SQLiteJobRepository,
):

    assert repository.next_available() is None


def test_next_available_returns_single_pending_job(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    assert repository.next_available().id == job.id


def test_next_available_prefers_highest_priority(
    repository: SQLiteJobRepository,
):

    low = create_job(
        name="low",
        priority=1,
    )

    medium = create_job(
        name="medium",
        priority=5,
    )

    high = create_job(
        name="high",
        priority=10,
    )

    repository.save(low)
    repository.save(high)
    repository.save(medium)

    job = repository.next_available()

    assert job is not None
    assert job.name == "high"


def test_next_available_breaks_priority_ties_by_creation_time(
    repository: SQLiteJobRepository,
):

    older = create_job(
        name="older",
        priority=5,
        now=utc(2025, 1, 1, 10),
    )

    newer = create_job(
        name="newer",
        priority=5,
        now=utc(2025, 1, 1, 11),
    )

    repository.save(newer)
    repository.save(older)

    job = repository.next_available()

    assert job is not None
    assert job.name == "older"


def test_next_available_ignores_processing_jobs(
    repository: SQLiteJobRepository,
):

    processing = create_job(
        name="processing",
    )

    repository.save(processing)

    processing.mark_processing()

    repository.update(processing)

    assert repository.next_available() is None


def test_next_available_ignores_future_jobs_with_default_now(
    repository: SQLiteJobRepository,
):

    now = datetime.now(UTC)

    future = create_job(
        name="future",
        priority=100,
        now=now,
    )

    repository.save(future)

    future.schedule_retry(3600)
    repository.update(future)

    available = create_job(
        name="available",
        priority=1,
        now=now,
    )

    repository.save(available)

    job = repository.next_available()

    assert job is not None
    assert job.name == "available"


def test_next_available_ignores_failed_jobs(
    repository: SQLiteJobRepository,
):

    failed = create_job()

    repository.save(failed)

    failed.mark_processing()
    failed.mark_failed("boom")

    repository.update(failed)

    assert repository.next_available() is None


def test_next_available_ignores_dead_jobs(
    repository: SQLiteJobRepository,
):

    dead = create_job()

    repository.save(dead)

    dead.move_to_dead()

    repository.update(dead)

    assert repository.next_available() is None


def test_next_available_returns_none_if_all_jobs_unavailable(
    repository: SQLiteJobRepository,
):

    future = create_job(priority=10)

    repository.save(future)

    future.schedule_retry(
        600,
        now=utc(2035, 1, 1),
    )

    repository.update(future)

    assert repository.next_available() is None


def test_next_available_skips_unavailable_high_priority_job(
    repository: SQLiteJobRepository,
):

    now = datetime.now(UTC)

    high = create_job(
        priority=100,
        now=now,
    )

    repository.save(high)

    high.schedule_retry(3600)
    repository.update(high)

    low = create_job(
        priority=1,
        now=now,
    )

    repository.save(low)

    job = repository.next_available()

    assert job is not None
    assert job.id == low.id


def test_next_available_returns_first_claimable_job(
    repository: SQLiteJobRepository,
):

    now = datetime.now(UTC)

    jobs = []

    for priority in [1, 4, 7, 10]:

        job = create_job(
            priority=priority,
            now=now,
        )

        repository.save(job)
        jobs.append(job)

    jobs[-1].schedule_retry(600)
    repository.update(jobs[-1])

    result = repository.next_available()

    assert result is not None
    assert result.priority == 7


# ----------------------------------------------------------------------
# Serialization
# ----------------------------------------------------------------------


def test_payload_round_trip(
    repository: SQLiteJobRepository,
):

    job = Job.create(
        name="complex",
        payload={
            "user": {
                "id": 1,
                "name": "Alice",
            },
            "numbers": [1, 2, 3],
            "enabled": True,
            "score": 91.5,
            "nested": {
                "x": {
                    "y": "z",
                },
            },
        },
    )

    repository.save(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.payload == job.payload


def test_datetime_fields_are_preserved(
    repository: SQLiteJobRepository,
):

    now = utc(2025, 1, 1, 12, 30)

    job = create_job(now=now)

    repository.save(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.created_at == now
    assert loaded.updated_at == now
    assert loaded.available_at == now


def test_worker_id_persistence(
    connection: SQLiteConnection,
    repository: SQLiteJobRepository,
):

    # Create worker repository
    worker_repository = SQLiteWorkerRepository(connection)

    # Insert worker into database
    worker = Worker.register(
        worker_id="worker-1",
        hostname="localhost",
    )

    worker_repository.save(worker)

    # Create and save job
    job = create_job()

    repository.save(job)

    # Claim using existing worker
    job.claim(worker.id)

    repository.update(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.worker_id == worker.id


def test_error_message_persistence(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    job.mark_processing()

    job.mark_failed("database timeout")

    repository.update(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.error_message == "database timeout"


def test_completed_timestamp_persistence(
    repository: SQLiteJobRepository,
):

    now = utc(2025, 1, 1)

    completed = now + timedelta(minutes=10)

    job = create_job(now=now)

    repository.save(job)

    job.mark_processing(now=now)

    job.mark_completed(now=completed)

    repository.update(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.completed_at == completed


def test_started_timestamp_persistence(
    repository: SQLiteJobRepository,
):

    start = utc(2025, 1, 1, 8)

    job = create_job(now=start)

    repository.save(job)

    job.mark_processing(now=start)

    repository.update(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.started_at == start


# ----------------------------------------------------------------------
# Repository Isolation
# ----------------------------------------------------------------------


def test_get_returns_new_instance(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    first = repository.get(job.id)

    second = repository.get(job.id)

    assert first is not second

    assert first == second


def test_repository_stores_updated_state(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    job.priority = 100

    repository.update(job)

    loaded = repository.get(job.id)

    assert loaded.priority == 100


def test_multiple_jobs_are_independent(
    repository: SQLiteJobRepository,
):

    first = create_job(name="A")

    second = create_job(name="B")

    repository.save(first)

    repository.save(second)

    first.priority = 50

    repository.update(first)

    loaded_first = repository.get(first.id)

    loaded_second = repository.get(second.id)

    assert loaded_first.priority == 50

    assert loaded_second.priority == 0


def test_repository_repr(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())

    text = repr(repository)

    assert "SQLiteJobRepository" in text

    assert "jobs=1" in text


# ----------------------------------------------------------------------
# Regression Tests
# ----------------------------------------------------------------------


def test_clear_then_reuse_repository(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())

    repository.clear()

    repository.save(create_job(name="new"))

    assert repository.count() == 1


def test_delete_then_insert_again(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    repository.delete(job.id)

    repository.save(job)

    assert repository.count() == 1


def test_empty_list_after_clear(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())

    repository.clear()

    assert repository.list() == []


def test_next_available_after_clear(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())

    repository.clear()

    assert repository.next_available() is None


# ----------------------------------------------------------------------
# Regression Tests
# ----------------------------------------------------------------------


def test_next_available_after_job_completion(
    repository: SQLiteJobRepository,
):

    first = create_job(
        name="first",
        priority=10,
    )

    second = create_job(
        name="second",
        priority=5,
    )

    repository.save(first)
    repository.save(second)

    first.mark_processing()
    first.mark_completed()

    repository.update(first)

    next_job = repository.next_available()

    assert next_job is not None
    assert next_job.name == "second"


def test_priority_order_is_preserved_after_updates(
    repository: SQLiteJobRepository,
):

    low = create_job(
        name="low",
        priority=1,
    )

    high = create_job(
        name="high",
        priority=5,
    )

    repository.save(low)
    repository.save(high)

    low.priority = 10

    repository.update(low)

    job = repository.next_available()

    assert job is not None
    assert job.name == "low"


def test_list_after_multiple_updates(
    repository: SQLiteJobRepository,
):

    jobs = []

    for i in range(5):

        job = create_job(
            name=f"job-{i}",
            priority=i,
        )

        repository.save(job)

        jobs.append(job)

    jobs[2].priority = 100
    repository.update(jobs[2])

    loaded = repository.get(jobs[2].id)

    assert loaded.priority == 100

    assert repository.count() == 5


def test_delete_does_not_affect_other_jobs(
    repository: SQLiteJobRepository,
):

    first = create_job(name="A")
    second = create_job(name="B")
    third = create_job(name="C")

    repository.save(first)
    repository.save(second)
    repository.save(third)

    repository.delete(second.id)

    assert repository.exists(first.id)
    assert repository.exists(third.id)

    assert repository.count() == 2


def test_list_after_delete_preserves_order(
    repository: SQLiteJobRepository,
):

    first = create_job(
        name="A",
        now=utc(2025, 1, 1, 10),
    )

    second = create_job(
        name="B",
        now=utc(2025, 1, 1, 11),
    )

    third = create_job(
        name="C",
        now=utc(2025, 1, 1, 12),
    )

    repository.save(first)
    repository.save(second)
    repository.save(third)

    repository.delete(second.id)

    jobs = repository.list()

    assert [job.name for job in jobs] == [
        "A",
        "C",
    ]


def test_update_does_not_create_duplicate_rows(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    for priority in range(10):

        job.priority = priority

        repository.update(job)

    assert repository.count() == 1


def test_clear_repository_multiple_times(
    repository: SQLiteJobRepository,
):

    repository.save(create_job())

    repository.clear()
    repository.clear()
    repository.clear()

    assert repository.count() == 0


def test_get_after_delete_returns_none(
    repository: SQLiteJobRepository,
):

    job = create_job()

    repository.save(job)

    repository.delete(job.id)

    assert repository.get(job.id) is None


def test_repository_can_store_many_jobs(
    repository: SQLiteJobRepository,
):

    total = 100

    for i in range(total):

        repository.save(
            create_job(
                name=f"job-{i}",
                priority=i % 10,
            )
        )

    assert repository.count() == total


def test_repository_handles_large_payload(
    repository: SQLiteJobRepository,
):

    payload = {
        "numbers": list(range(1000)),
        "text": "QueueCTL" * 500,
    }

    job = Job.create(
        name="large",
        payload=payload,
    )

    repository.save(job)

    loaded = repository.get(job.id)

    assert loaded is not None
    assert loaded.payload == payload


# ----------------------------------------------------------------------
# Smoke Test
# ----------------------------------------------------------------------


def test_complete_repository_lifecycle(
    repository: SQLiteJobRepository,
):

    job = create_job(
        name="email",
        priority=5,
    )

    repository.save(job)

    assert repository.exists(job.id)

    loaded = repository.get(job.id)

    assert loaded is not None

    loaded.mark_processing()

    repository.update(loaded)

    processing = repository.get(job.id)

    assert processing.state == JobState.PROCESSING

    processing.mark_completed()

    repository.update(processing)

    completed = repository.get(job.id)

    assert completed.state == JobState.COMPLETED

    repository.delete(job.id)

    assert repository.count() == 0

    assert repository.get(job.id) is None
