"""Unit tests for :mod:`queuectl.domain.entities.job`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from queuectl.domain.entities.job import Job
from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState

FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
LATER = FIXED_NOW + timedelta(seconds=30)
EVEN_LATER = FIXED_NOW + timedelta(seconds=90)


def make_job(**overrides: object) -> Job:
    """Build a ``PENDING`` job with predictable defaults for testing.

    Args:
        **overrides: Keyword arguments forwarded to :meth:`Job.create`,
            overriding the defaults below.

    Returns:
        Job: A newly created job stamped with :data:`FIXED_NOW`.
    """
    params: dict[str, object] = {
        "name": "send-email",
        "payload": {"to": "user@example.com"},
        "priority": 1,
        "now": FIXED_NOW,
    }
    params.update(overrides)
    return Job.create(**params)  # type: ignore[arg-type]


class TestCreate:
    """Tests for :meth:`Job.create`."""

    def test_create_sets_pending_state(self) -> None:
        job = make_job()
        assert job.state is JobState.PENDING

    def test_create_defaults_payload_to_empty_dict(self) -> None:
        job = Job.create(name="noop", now=FIXED_NOW)
        assert job.payload == {}

    def test_create_defaults_priority_to_zero(self) -> None:
        job = Job.create(name="noop", now=FIXED_NOW)
        assert job.priority == 0

    def test_create_defaults_retry_count_to_zero(self) -> None:
        job = make_job()
        assert job.retry_count == 0

    def test_create_sets_created_and_updated_at_equal(self) -> None:
        job = make_job()
        assert job.created_at == job.updated_at == FIXED_NOW

    def test_create_sets_available_at_to_created_at(self) -> None:
        job = make_job()
        assert job.available_at == job.created_at

    def test_create_generates_job_id_when_not_provided(self) -> None:
        job = make_job()
        assert isinstance(job.id, JobId)

    def test_create_uses_explicit_job_id(self) -> None:
        explicit_id = JobId.generate()
        job = make_job(job_id=explicit_id)
        assert job.id == explicit_id

    def test_create_leaves_optional_fields_none(self) -> None:
        job = make_job()
        assert job.started_at is None
        assert job.completed_at is None
        assert job.worker_id is None
        assert job.error_message is None

    def test_create_without_now_uses_current_time(self) -> None:
        before = datetime.now(UTC)
        job = Job.create(name="noop")
        after = datetime.now(UTC)
        assert before <= job.created_at <= after

    def test_create_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError):
            Job.create(name="", now=FIXED_NOW)

    def test_create_rejects_negative_priority(self) -> None:
        with pytest.raises(ValueError):
            make_job(priority=-1)

    def test_create_accepts_zero_priority(self) -> None:
        job = make_job(priority=0)
        assert job.priority == 0


class TestCanBeClaimed:
    """Tests for :meth:`Job.can_be_claimed`."""

    def test_pending_and_available_job_can_be_claimed(self) -> None:
        job = make_job()
        assert job.can_be_claimed(now=FIXED_NOW) is True

    def test_job_not_yet_available_cannot_be_claimed(self) -> None:
        job = make_job()
        job.available_at = LATER
        assert job.can_be_claimed(now=FIXED_NOW) is False

    def test_processing_job_cannot_be_claimed(self) -> None:
        job = make_job()
        job.claim("worker-1", now=FIXED_NOW)
        assert job.can_be_claimed(now=LATER) is False

    def test_dead_job_cannot_be_claimed(self) -> None:
        job = make_job()
        job.move_to_dead(now=FIXED_NOW)
        assert job.can_be_claimed(now=LATER) is False

    def test_can_be_claimed_defaults_now_to_current_time(self) -> None:
        job = make_job(now=datetime.now(UTC) - timedelta(seconds=1))
        assert job.can_be_claimed() is True


class TestClaim:
    """Tests for :meth:`Job.claim`."""

    def test_claim_transitions_to_processing(self) -> None:
        job = make_job()
        job.claim("worker-1", now=LATER)
        assert job.state is JobState.PROCESSING

    def test_claim_sets_worker_id(self) -> None:
        job = make_job()
        job.claim("worker-1", now=LATER)
        assert job.worker_id == "worker-1"

    def test_claim_sets_started_at(self) -> None:
        job = make_job()
        job.claim("worker-1", now=LATER)
        assert job.started_at == LATER

    def test_claim_updates_updated_at(self) -> None:
        job = make_job()
        job.claim("worker-1", now=LATER)
        assert job.updated_at == LATER

    def test_claim_rejects_empty_worker_id(self) -> None:
        job = make_job()
        with pytest.raises(ValueError):
            job.claim("", now=LATER)

    def test_claim_processing_job_raises(self) -> None:
        job = make_job()
        job.claim("worker-1", now=LATER)
        with pytest.raises(ValueError):
            job.claim("worker-2", now=EVEN_LATER)

    def test_claim_dead_job_raises(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        with pytest.raises(ValueError):
            job.claim("worker-1", now=EVEN_LATER)

    def test_claim_completed_job_raises(self) -> None:
        job = make_job()
        job.claim("worker-1", now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.claim("worker-2", now=EVEN_LATER)

    def test_claim_not_yet_available_job_raises(self) -> None:
        job = make_job()
        job.available_at = EVEN_LATER
        with pytest.raises(ValueError):
            job.claim("worker-1", now=LATER)


class TestMarkProcessing:
    """Tests for :meth:`Job.mark_processing`."""

    def test_mark_processing_from_pending_succeeds(self) -> None:
        job = make_job()
        job.mark_processing(now=LATER)
        assert job.state is JobState.PROCESSING

    def test_mark_processing_sets_started_at(self) -> None:
        job = make_job()
        job.mark_processing(now=LATER)
        assert job.started_at == LATER

    def test_mark_processing_already_processing_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=LATER)
        with pytest.raises(ValueError):
            job.mark_processing(now=EVEN_LATER)

    def test_mark_processing_completed_job_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.mark_processing(now=EVEN_LATER)

    def test_mark_processing_dead_job_raises(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        with pytest.raises(ValueError):
            job.mark_processing(now=EVEN_LATER)


class TestMarkCompleted:
    """Tests for :meth:`Job.mark_completed`."""

    def test_mark_completed_from_processing_succeeds(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        assert job.state is JobState.COMPLETED

    def test_mark_completed_sets_completed_at(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        assert job.completed_at == LATER

    def test_mark_completed_clears_error_message(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.schedule_retry(0, now=LATER)
        job.mark_processing(now=EVEN_LATER)
        job.mark_completed(now=EVEN_LATER)
        assert job.error_message is None

    def test_mark_completed_from_pending_raises(self) -> None:
        job = make_job()
        with pytest.raises(ValueError):
            job.mark_completed(now=LATER)

    def test_mark_completed_already_completed_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.mark_completed(now=EVEN_LATER)

    def test_mark_completed_dead_job_raises(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        with pytest.raises(ValueError):
            job.mark_completed(now=EVEN_LATER)


class TestMarkFailed:
    """Tests for :meth:`Job.mark_failed`."""

    def test_mark_failed_from_processing_succeeds(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("connection refused", now=LATER)
        assert job.state is JobState.FAILED

    def test_mark_failed_sets_error_message(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("connection refused", now=LATER)
        assert job.error_message == "connection refused"

    def test_mark_failed_updates_updated_at(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("connection refused", now=LATER)
        assert job.updated_at == LATER

    def test_mark_failed_rejects_empty_message(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        with pytest.raises(ValueError):
            job.mark_failed("", now=LATER)

    def test_mark_failed_from_pending_raises(self) -> None:
        job = make_job()
        with pytest.raises(ValueError):
            job.mark_failed("boom", now=LATER)

    def test_mark_failed_completed_job_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.mark_failed("boom", now=EVEN_LATER)

    def test_mark_failed_dead_job_raises(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        with pytest.raises(ValueError):
            job.mark_failed("boom", now=EVEN_LATER)


class TestIncrementRetry:
    """Tests for :meth:`Job.increment_retry`."""

    def test_increment_retry_increases_count(self) -> None:
        job = make_job()
        job.increment_retry(now=LATER)
        assert job.retry_count == 1

    def test_increment_retry_does_not_change_state(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.increment_retry(now=EVEN_LATER)
        assert job.state is JobState.FAILED

    def test_increment_retry_updates_updated_at(self) -> None:
        job = make_job()
        job.increment_retry(now=LATER)
        assert job.updated_at == LATER

    def test_increment_retry_is_cumulative(self) -> None:
        job = make_job()
        job.increment_retry(now=LATER)
        job.increment_retry(now=EVEN_LATER)
        assert job.retry_count == 2

    def test_increment_retry_on_completed_job_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.increment_retry(now=EVEN_LATER)

    def test_increment_retry_on_dead_job_raises(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        with pytest.raises(ValueError):
            job.increment_retry(now=EVEN_LATER)


class TestScheduleRetry:
    """Tests for :meth:`Job.schedule_retry`."""

    def test_schedule_retry_sets_state_to_pending(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.schedule_retry(60, now=LATER)
        assert job.state is JobState.PENDING

    def test_schedule_retry_pushes_available_at_forward(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.schedule_retry(60, now=LATER)
        assert job.available_at == LATER + timedelta(seconds=60)

    def test_schedule_retry_does_not_increment_retry_count(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.schedule_retry(60, now=LATER)
        assert job.retry_count == 0

    def test_schedule_retry_updates_updated_at(self) -> None:
        job = make_job()
        job.schedule_retry(10, now=LATER)
        assert job.updated_at == LATER

    def test_schedule_retry_accepts_zero_delay(self) -> None:
        job = make_job()
        job.schedule_retry(0, now=LATER)
        assert job.available_at == LATER

    def test_schedule_retry_rejects_negative_delay(self) -> None:
        job = make_job()
        with pytest.raises(ValueError):
            job.schedule_retry(-1, now=LATER)

    def test_schedule_retry_on_completed_job_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.schedule_retry(10, now=EVEN_LATER)

    def test_schedule_retry_on_dead_job_raises(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        with pytest.raises(ValueError):
            job.schedule_retry(10, now=EVEN_LATER)


class TestMoveToDead:
    """Tests for :meth:`Job.move_to_dead`."""

    def test_move_to_dead_from_failed_succeeds(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.move_to_dead(now=EVEN_LATER)
        assert job.state is JobState.DEAD

    def test_move_to_dead_from_pending_succeeds(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        assert job.state is JobState.DEAD

    def test_move_to_dead_updates_updated_at(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        assert job.updated_at == LATER

    def test_move_to_dead_from_completed_raises(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        with pytest.raises(ValueError):
            job.move_to_dead(now=EVEN_LATER)

    def test_move_to_dead_is_idempotent(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        job.move_to_dead(now=EVEN_LATER)
        assert job.state is JobState.DEAD
        assert job.updated_at == EVEN_LATER


class TestReset:
    """Tests for :meth:`Job.reset`."""

    def test_reset_sets_state_to_pending(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        job.reset(now=EVEN_LATER)
        assert job.state is JobState.PENDING

    def test_reset_clears_retry_count(self) -> None:
        job = make_job()
        job.increment_retry(now=LATER)
        job.increment_retry(now=LATER)
        job.reset(now=EVEN_LATER)
        assert job.retry_count == 0

    def test_reset_clears_worker_id(self) -> None:
        job = make_job()
        job.claim("worker-1", now=LATER)
        job.reset(now=EVEN_LATER)
        assert job.worker_id is None

    def test_reset_clears_started_and_completed_at(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        job.reset(now=EVEN_LATER)
        assert job.started_at is None
        assert job.completed_at is None

    def test_reset_clears_error_message(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        job.reset(now=EVEN_LATER)
        assert job.error_message is None

    def test_reset_sets_available_at_to_now(self) -> None:
        job = make_job()
        job.schedule_retry(3600, now=LATER)
        job.reset(now=EVEN_LATER)
        assert job.available_at == EVEN_LATER

    def test_reset_updates_updated_at(self) -> None:
        job = make_job()
        job.reset(now=EVEN_LATER)
        assert job.updated_at == EVEN_LATER


class TestStatePredicates:
    """Tests for the boolean state-query methods."""

    def test_is_terminal_false_for_pending(self) -> None:
        assert make_job().is_terminal() is False

    def test_is_terminal_true_for_completed(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        assert job.is_terminal() is True

    def test_is_terminal_true_for_dead(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        assert job.is_terminal() is True

    def test_is_completed_true_only_when_completed(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        assert job.is_completed() is True
        assert job.is_failed() is False
        assert job.is_dead() is False
        assert job.is_processing() is False

    def test_is_failed_true_only_when_failed(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("boom", now=LATER)
        assert job.is_failed() is True
        assert job.is_completed() is False
        assert job.is_dead() is False
        assert job.is_processing() is False

    def test_is_dead_true_only_when_dead(self) -> None:
        job = make_job()
        job.move_to_dead(now=LATER)
        assert job.is_dead() is True
        assert job.is_completed() is False
        assert job.is_failed() is False
        assert job.is_processing() is False

    def test_is_processing_true_only_when_processing(self) -> None:
        job = make_job()
        job.mark_processing(now=LATER)
        assert job.is_processing() is True
        assert job.is_completed() is False
        assert job.is_failed() is False
        assert job.is_dead() is False


class TestTouch:
    """Tests for :meth:`Job.touch`."""

    def test_touch_updates_updated_at(self) -> None:
        job = make_job()
        job.touch(now=LATER)
        assert job.updated_at == LATER

    def test_touch_does_not_change_state(self) -> None:
        job = make_job()
        job.touch(now=LATER)
        assert job.state is JobState.PENDING

    def test_touch_does_not_change_other_fields(self) -> None:
        job = make_job()
        job.touch(now=LATER)
        assert job.retry_count == 0
        assert job.worker_id is None

    def test_touch_defaults_now_to_current_time(self) -> None:
        job = make_job()
        before = datetime.now(UTC)
        job.touch()
        after = datetime.now(UTC)
        assert before <= job.updated_at <= after


class TestSerialization:
    """Tests for :meth:`Job.to_dict` and :meth:`Job.from_dict`."""

    def test_to_dict_serializes_id_as_string(self) -> None:
        job = make_job()
        assert job.to_dict()["id"] == str(job.id)
        assert isinstance(job.to_dict()["id"], str)

    def test_to_dict_serializes_state_as_string(self) -> None:
        job = make_job()
        assert job.to_dict()["state"] == JobState.PENDING.value

    def test_to_dict_serializes_datetimes_as_iso8601(self) -> None:
        job = make_job()
        data = job.to_dict()
        assert data["created_at"] == FIXED_NOW.isoformat()
        assert data["updated_at"] == FIXED_NOW.isoformat()
        assert data["available_at"] == FIXED_NOW.isoformat()

    def test_to_dict_serializes_none_optional_datetimes_as_none(self) -> None:
        job = make_job()
        data = job.to_dict()
        assert data["started_at"] is None
        assert data["completed_at"] is None

    def test_to_dict_serializes_populated_optional_datetimes(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_completed(now=LATER)
        data = job.to_dict()
        assert data["started_at"] == FIXED_NOW.isoformat()
        assert data["completed_at"] == LATER.isoformat()

    def test_to_dict_includes_payload_priority_and_retry_count(self) -> None:
        job = make_job(payload={"key": "value"}, priority=5)
        data = job.to_dict()
        assert data["payload"] == {"key": "value"}
        assert data["priority"] == 5
        assert data["retry_count"] == 0

    def test_from_dict_round_trips_to_equal_job(self) -> None:
        original = make_job()
        original.claim("worker-1", now=LATER)
        reconstructed = Job.from_dict(original.to_dict())
        assert reconstructed == original

    def test_from_dict_round_trips_terminal_job(self) -> None:
        original = make_job()
        original.mark_processing(now=FIXED_NOW)
        original.mark_failed("boom", now=LATER)
        original.move_to_dead(now=EVEN_LATER)
        reconstructed = Job.from_dict(original.to_dict())
        assert reconstructed == original
        assert reconstructed.is_dead() is True

    def test_from_dict_parses_job_id_correctly(self) -> None:
        job = make_job()
        reconstructed = Job.from_dict(job.to_dict())
        assert reconstructed.id == job.id

    def test_from_dict_parses_state_correctly(self) -> None:
        job = make_job()
        job.mark_processing(now=LATER)
        reconstructed = Job.from_dict(job.to_dict())
        assert reconstructed.state is JobState.PROCESSING

    def test_from_dict_handles_missing_optional_keys(self) -> None:
        job = make_job()
        data = job.to_dict()
        del data["worker_id"]
        del data["error_message"]
        reconstructed = Job.from_dict(data)
        assert reconstructed.worker_id is None
        assert reconstructed.error_message is None

    def test_from_dict_raises_on_missing_required_key(self) -> None:
        job = make_job()
        data = job.to_dict()
        del data["name"]
        with pytest.raises(KeyError):
            Job.from_dict(data)

    def test_from_dict_raises_on_invalid_state(self) -> None:
        job = make_job()
        data = job.to_dict()
        data["state"] = "not-a-real-state"
        with pytest.raises(ValueError):
            Job.from_dict(data)


class TestRepr:
    """Tests for :meth:`Job.__repr__`."""

    def test_repr_contains_key_fields(self) -> None:
        job = make_job(priority=3)
        text = repr(job)
        assert "Job(" in text
        assert str(job.id) in text or repr(job.id) in text
        assert job.name in text
        assert "PENDING" in text or JobState.PENDING.value in text
        assert "priority=3" in text
        assert "retry_count=0" in text

    def test_repr_reflects_updated_state(self) -> None:
        job = make_job()
        job.mark_processing(now=LATER)
        text = repr(job)
        assert "PROCESSING" in text or JobState.PROCESSING.value in text


class TestEdgeCases:
    """Additional edge-case coverage across the job lifecycle."""

    def test_full_lifecycle_pending_to_dead_via_retries(self) -> None:
        job = make_job()
        job.mark_processing(now=FIXED_NOW)
        job.mark_failed("timeout", now=LATER)
        job.increment_retry(now=LATER)
        job.schedule_retry(5, now=LATER)
        assert job.state is JobState.PENDING
        assert job.retry_count == 1

        job.mark_processing(now=EVEN_LATER)
        job.mark_failed("timeout again", now=EVEN_LATER)
        job.increment_retry(now=EVEN_LATER)
        job.move_to_dead(now=EVEN_LATER)

        assert job.is_dead() is True
        assert job.retry_count == 2
        assert job.error_message == "timeout again"

    def test_priority_boundary_value_zero_is_valid(self) -> None:
        job = make_job(priority=0)
        assert job.priority == 0

    def test_large_priority_value_is_valid(self) -> None:
        job = make_job(priority=1_000_000)
        assert job.priority == 1_000_000

    def test_schedule_retry_with_fractional_seconds(self) -> None:
        job = make_job()
        job.schedule_retry(1.5, now=FIXED_NOW)
        assert job.available_at == FIXED_NOW + timedelta(seconds=1.5)

    def test_payload_supports_nested_structures(self) -> None:
        payload = {"nested": {"list": [1, 2, 3], "flag": True}}
        job = make_job(payload=payload)
        assert job.to_dict()["payload"] == payload

    def test_two_jobs_with_same_fields_are_equal(self) -> None:
        job_id = JobId.generate()
        first = make_job(job_id=job_id)
        second = make_job(job_id=job_id)
        assert first == second

    def test_two_jobs_with_different_ids_are_not_equal(self) -> None:
        first = make_job()
        second = make_job()
        assert first != second
