import pytest

from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.backoff_policy import (
    BackoffPolicy,
    BackoffStrategy,
)


def test_default_retry_policy():
    policy = RetryPolicy()

    assert policy.max_retries == 3
    assert policy.has_retries


def test_retry_allowed():
    policy = RetryPolicy(max_retries=3)

    assert policy.should_retry(0)
    assert policy.should_retry(1)
    assert policy.should_retry(2)


def test_retry_not_allowed():
    policy = RetryPolicy(max_retries=3)

    assert not policy.should_retry(3)
    assert not policy.should_retry(4)


def test_retry_exhausted():
    policy = RetryPolicy(max_retries=2)

    assert not policy.is_exhausted(0)
    assert not policy.is_exhausted(1)
    assert policy.is_exhausted(2)


def test_first_retry_delay():
    policy = RetryPolicy(
        max_retries=3,
        backoff=BackoffPolicy(
            strategy=BackoffStrategy.FIXED,
            initial_delay=10,
        ),
    )

    assert policy.next_retry_delay(0) == 10


def test_second_retry_delay():
    policy = RetryPolicy(
        max_retries=5,
        backoff=BackoffPolicy(
            strategy=BackoffStrategy.EXPONENTIAL,
            initial_delay=5,
            multiplier=2,
        ),
    )

    assert policy.next_retry_delay(0) == 5
    assert policy.next_retry_delay(1) == 10
    assert policy.next_retry_delay(2) == 20


def test_retry_limit_exception():
    policy = RetryPolicy(max_retries=2)

    with pytest.raises(RuntimeError):
        policy.next_retry_delay(2)


def test_negative_retry_count():
    policy = RetryPolicy()

    with pytest.raises(ValueError):
        policy.should_retry(-1)


def test_negative_max_retries():
    with pytest.raises(ValueError):
        RetryPolicy(max_retries=-1)


def test_zero_retries():
    policy = RetryPolicy(max_retries=0)

    assert not policy.has_retries
    assert not policy.should_retry(0)


def test_string_representation():
    policy = RetryPolicy()

    assert "RetryPolicy" in str(policy)