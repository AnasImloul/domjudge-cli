"""Rate limiter for API requests.

This module implements a token bucket rate limiter to prevent overwhelming
the API server with too many requests.
"""

import time
from threading import Lock

from dom.exceptions import APIRateLimitError
from dom.logging_config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Limits the rate of operations using a token bucket algorithm.
    Thread-safe implementation.
    """

    def __init__(self, rate: float = 10.0, burst: int = 20):
        """
        Initialize the rate limiter.

        Args:
            rate: Requests per second allowed (default: 10)
            burst: Maximum burst size (default: 20)
        """
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_update = time.time()
        self._lock = Lock()

        logger.info(f"Rate limiter initialized: {rate} req/s, burst: {burst}")

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.rate
        self._tokens = min(self.burst, self._tokens + new_tokens)
        self._last_update = now

    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire
            blocking: If True, wait until tokens are available

        Returns:
            True if tokens were acquired, False if not available and non-blocking

        Raises:
            APIRateLimitError: If tokens cannot be acquired and blocking is False
        """
        with self._lock:
            self._refill_tokens()

            if self._tokens >= tokens:
                self._tokens -= tokens
                logger.debug(f"Acquired {tokens} token(s), {self._tokens:.2f} remaining")
                return True

            if not blocking:
                wait_time = (tokens - self._tokens) / self.rate
                logger.warning(f"Rate limit would be exceeded, need to wait {wait_time:.2f}s")
                raise APIRateLimitError(
                    f"Rate limit exceeded. Try again in {wait_time:.2f} seconds."
                )

            # Calculate wait time
            wait_time = (tokens - self._tokens) / self.rate
            logger.info(f"Rate limit reached, waiting {wait_time:.2f}s...")

        # Wait outside the lock to allow other threads
        time.sleep(wait_time)

        # Try again
        with self._lock:
            self._refill_tokens()
            if self._tokens >= tokens:
                self._tokens -= tokens
                logger.debug(f"Acquired {tokens} token(s) after waiting")
                return True

            # Should not happen, but handle gracefully
            logger.error("Failed to acquire tokens after waiting")
            return False

    def reset(self) -> None:
        """Reset the rate limiter to full capacity."""
        with self._lock:
            self._tokens = float(self.burst)
            self._last_update = time.time()
            logger.debug("Rate limiter reset")
