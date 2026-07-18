import pytest

from queuectl.domain.value_objects.backoff_policy import (
    BackoffPolicy,
    BackoffStrategy,
)


def test_default_policy():
    policy = BackoffPolicy()

    assert policy.strategy is BackoffStrategy.EXPONENTIAL
    assert policy.initial_delay == 5
    assert policy.multiplier == 2.0
    assert policy.max_delay == 300


def test_fixed_strategy():
    policy = BackoffPolicy(
        strategy=BackoffStrategy.FIXED,
        initial_delay=10,
    )

    assert policy.get_delay(1) == 10
    assert policy.get_delay(2) == 10
    assert policy.get_delay(10) == 10


def test_linear_strategy():
    policy = BackoffPolicy(
        strategy=BackoffStrategy.LINEAR,
        initial_delay=5,
    )

    assert policy.get_delay(1) == 5
    assert policy.get_delay(2) == 10
    assert policy.get_delay(3) == 15
    assert policy.get_delay(4) == 20


def test_exponential_strategy():
    policy = BackoffPolicy(
        strategy=BackoffStrategy.EXPONENTIAL,
        initial_delay=5,
        multiplier=2,
    )

    assert policy.get_delay(1) == 5
    assert policy.get_delay(2) == 10
    assert policy.get_delay(3) == 20
    assert policy.get_delay(4) == 40


def test_max_delay():
    policy = BackoffPolicy(
        initial_delay=20,
        multiplier=2,
        max_delay=50,
    )

    assert policy.get_delay(1) == 20
    assert policy.get_delay(2) == 40
    assert policy.get_delay(3) == 50
    assert policy.get_delay(10) == 50


def test_invalid_attempt():
    policy = BackoffPolicy()

    with pytest.raises(ValueError):
        policy.get_delay(0)

    with pytest.raises(ValueError):
        policy.get_delay(-2)


def test_invalid_initial_delay():
    with pytest.raises(ValueError):
        BackoffPolicy(initial_delay=0)


def test_invalid_multiplier():
    with pytest.raises(ValueError):
        BackoffPolicy(multiplier=0.5)


def test_invalid_max_delay():
    with pytest.raises(ValueError):
        BackoffPolicy(
            initial_delay=10,
            max_delay=5,
        )


def test_strategy_properties():
    fixed = BackoffPolicy(strategy=BackoffStrategy.FIXED)
    linear = BackoffPolicy(strategy=BackoffStrategy.LINEAR)
    expo = BackoffPolicy(strategy=BackoffStrategy.EXPONENTIAL)

    assert fixed.is_fixed
    assert not fixed.is_linear

    assert linear.is_linear
    assert not linear.is_exponential

    assert expo.is_exponential
    assert not expo.is_fixed


def test_string_representation():
    policy = BackoffPolicy()

    assert "exponential" in str(policy)
