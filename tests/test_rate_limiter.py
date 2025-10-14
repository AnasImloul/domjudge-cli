"""Tests for rate limiter."""

import time

import pytest

from dom.exceptions import APIRateLimitError
from dom.infrastructure.api.rate_limiter import RateLimiter


def test_rate_limiter_acquire():
    """Test basic token acquisition."""
    limiter = RateLimiter(rate=10.0, burst=10)

    # Should be able to acquire tokens
    result = limiter.acquire(1)
    assert result is True


def test_rate_limiter_burst():
    """Test burst capacity."""
    limiter = RateLimiter(rate=10.0, burst=5)

    # Should be able to acquire up to burst size immediately
    for _ in range(5):
        result = limiter.acquire(1, blocking=False)
        assert result is True

    # Next acquisition should fail (non-blocking)
    with pytest.raises(APIRateLimitError):
        limiter.acquire(1, blocking=False)


def test_rate_limiter_refill():
    """Test that tokens refill over time."""
    limiter = RateLimiter(rate=10.0, burst=2)

    # Use up all tokens
    limiter.acquire(2)

    # Wait for refill (at 10 tokens/sec, 0.1s = 1 token)
    time.sleep(0.15)

    # Should be able to acquire 1 token
    result = limiter.acquire(1, blocking=False)
    assert result is True


def test_rate_limiter_blocking():
    """Test blocking acquisition."""
    limiter = RateLimiter(rate=10.0, burst=1)

    # Use up all tokens
    limiter.acquire(1)

    start = time.time()
    # This should block until tokens are available
    limiter.acquire(1, blocking=True)
    elapsed = time.time() - start

    # Should have waited approximately 0.1 seconds (1/10 rate)
    assert elapsed >= 0.05  # Allow some timing variance


def test_rate_limiter_reset():
    """Test rate limiter reset."""
    limiter = RateLimiter(rate=10.0, burst=5)

    # Use up tokens
    limiter.acquire(5)

    # Reset should restore full capacity
    limiter.reset()

    # Should be able to acquire burst size again
    result = limiter.acquire(5, blocking=False)
    assert result is True
