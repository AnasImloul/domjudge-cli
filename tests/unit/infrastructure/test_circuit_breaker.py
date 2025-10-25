"""Tests for circuit breaker pattern."""

import time

import pytest

from dom.infrastructure.api.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)


def test_circuit_breaker_starts_closed():
    """Test that circuit breaker starts in CLOSED state."""
    breaker = CircuitBreaker("test")
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_opens_after_failures():
    """Test that circuit breaker opens after threshold failures."""
    breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))

    # First two failures - should stay closed
    for _ in range(2):
        try:
            with breaker:
                raise Exception("Test error")
        except Exception:
            pass

    assert breaker.state == CircuitState.CLOSED

    # Third failure - should open
    try:
        with breaker:
            raise Exception("Test error")
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_rejects_when_open():
    """Test that circuit breaker rejects calls when OPEN."""
    breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))

    # Cause failure to open circuit
    try:
        with breaker:
            raise Exception("Test error")
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN

    # Next call should be rejected immediately
    with pytest.raises(CircuitBreakerError):
        with breaker:
            pass


def test_circuit_breaker_transitions_to_half_open():
    """Test that circuit breaker transitions to HALF_OPEN after timeout."""
    breaker = CircuitBreaker(
        "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
    )

    # Open the circuit
    try:
        with breaker:
            raise Exception("Test error")
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)

    # Should now be in HALF_OPEN when we try
    # (transition happens on call attempt)
    with breaker:
        pass  # Success

    # After success in HALF_OPEN with default success_threshold=2,
    # should still be in HALF_OPEN or become CLOSED
    assert breaker.state in [CircuitState.HALF_OPEN, CircuitState.CLOSED]


def test_circuit_breaker_closes_after_successes():
    """Test that circuit breaker closes after success threshold."""
    breaker = CircuitBreaker(
        "test",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, success_threshold=2),
    )

    # Open the circuit
    try:
        with breaker:
            raise Exception("Test error")
    except Exception:
        pass

    # Wait for recovery
    time.sleep(0.15)

    # Two successful calls should close circuit
    for _ in range(2):
        with breaker:
            pass

    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_reopens_on_failure_in_half_open():
    """Test that circuit reopens if call fails in HALF_OPEN state."""
    breaker = CircuitBreaker(
        "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
    )

    # Open the circuit
    try:
        with breaker:
            raise Exception("Test error")
    except Exception:
        pass

    # Wait for recovery
    time.sleep(0.15)

    # Fail in HALF_OPEN state
    try:
        with breaker:
            raise Exception("Still failing")
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_reset():
    """Test manual circuit breaker reset."""
    breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))

    # Open the circuit
    try:
        with breaker:
            raise Exception("Test error")
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN

    # Manual reset
    breaker.reset()

    assert breaker.state == CircuitState.CLOSED
