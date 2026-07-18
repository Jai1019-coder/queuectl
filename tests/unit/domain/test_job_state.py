import pytest

from queuectl.domain.value_objects.job_state import JobState


def test_enum_values():
    assert JobState.PENDING.value == "pending"
    assert JobState.PROCESSING.value == "processing"
    assert JobState.COMPLETED.value == "completed"
    assert JobState.FAILED.value == "failed"
    assert JobState.DEAD.value == "dead"


def test_terminal_states():
    assert JobState.COMPLETED.is_terminal
    assert JobState.DEAD.is_terminal

    assert not JobState.PENDING.is_terminal
    assert not JobState.PROCESSING.is_terminal
    assert not JobState.FAILED.is_terminal


def test_retryable_state():
    assert JobState.FAILED.can_retry

    assert not JobState.PENDING.can_retry
    assert not JobState.PROCESSING.can_retry
    assert not JobState.COMPLETED.can_retry
    assert not JobState.DEAD.can_retry


def test_claimable():
    assert JobState.PENDING.can_be_claimed

    assert not JobState.PROCESSING.can_be_claimed
    assert not JobState.COMPLETED.can_be_claimed
    assert not JobState.FAILED.can_be_claimed
    assert not JobState.DEAD.can_be_claimed


def test_active_state():
    assert JobState.PROCESSING.is_active

    assert not JobState.PENDING.is_active
    assert not JobState.COMPLETED.is_active
    assert not JobState.FAILED.is_active
    assert not JobState.DEAD.is_active


def test_string_conversion():
    assert str(JobState.PENDING) == "pending"
    assert str(JobState.DEAD) == "dead"


@pytest.mark.parametrize(
    "state",
    [
        JobState.PENDING,
        JobState.PROCESSING,
        JobState.COMPLETED,
        JobState.FAILED,
        JobState.DEAD,
    ],
)
def test_all_states_are_unique(state):
    assert list(JobState).count(state) == 1
