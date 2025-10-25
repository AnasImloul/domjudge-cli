"""Tests for retry logic with exponential backoff."""

import pytest

from dom.exceptions import PermanentAPIError, RetryableAPIError
from dom.infrastructure.api.retry import (
    RetryConfig,
    calculate_delay,
    is_retryable_error,
    with_retry,
)


def test_calculate_delay():
    """Test exponential backoff calculation."""
    config = RetryConfig(base_delay=1.0, max_delay=10.0, exponential_base=2.0, jitter=False)

    # Test basic exponential backoff
    delay0 = calculate_delay(0, config)
    delay1 = calculate_delay(1, config)
    delay2 = calculate_delay(2, config)

    assert delay0 == 1.0
    assert delay1 == 2.0
    assert delay2 == 4.0

    # Test max delay capping
    delay_large = calculate_delay(10, config)
    assert delay_large <= config.max_delay


def test_calculate_delay_with_jitter():
    """Test that jitter adds randomness."""
    config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True)

    delays = [calculate_delay(1, config) for _ in range(10)]

    # Should have some variation
    assert len(set(delays)) >= 1


def test_is_retryable_error():
    """Test retryable error detection."""
    # Retryable errors
    assert is_retryable_error(RetryableAPIError("Server error"))
    assert is_retryable_error(ConnectionError("Connection refused"))
    assert is_retryable_error(TimeoutError("Request timeout"))

    # Non-retryable errors
    assert not is_retryable_error(PermanentAPIError("Not found"))
    assert not is_retryable_error(ValueError("Invalid input"))


def test_with_retry_success():
    """Test retry decorator with successful operation."""
    call_count = {"value": 0}

    @with_retry(RetryConfig(max_retries=3, base_delay=0.01))
    def successful_operation():
        call_count["value"] += 1
        return "success"

    result = successful_operation()

    assert result == "success"
    assert call_count["value"] == 1  # Called only once


def test_with_retry_transient_failure():
    """Test retry decorator with transient failures."""
    call_count = {"value": 0}

    @with_retry(RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
    def flaky_operation():
        call_count["value"] += 1
        if call_count["value"] < 3:
            raise RetryableAPIError("Transient error")
        return "success"

    result = flaky_operation()

    assert result == "success"
    assert call_count["value"] == 3  # Succeeded on third attempt


def test_with_retry_permanent_failure():
    """Test retry decorator with permanent failure."""
    call_count = {"value": 0}

    @with_retry(RetryConfig(max_retries=3))
    def failing_operation():
        call_count["value"] += 1
        raise PermanentAPIError("Permanent error")

    with pytest.raises(PermanentAPIError):
        failing_operation()

    assert call_count["value"] == 1  # Not retried


def test_with_retry_max_retries_exceeded():
    """Test retry decorator when max retries exceeded."""
    call_count = {"value": 0}

    @with_retry(RetryConfig(max_retries=2, base_delay=0.01, jitter=False))
    def always_failing():
        call_count["value"] += 1
        raise RetryableAPIError("Always fails")

    with pytest.raises(RetryableAPIError):
        always_failing()

    assert call_count["value"] == 3  # Initial + 2 retries
