"""Retry logic with exponential backoff for API requests.

This module provides retry mechanisms for handling transient failures
in API communications.
"""

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from dom.exceptions import APIRateLimitError, PermanentAPIError, RetryableAPIError
from dom.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for a retry attempt with exponential backoff.

    Args:
        attempt: Current retry attempt (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    delay = min(config.base_delay * (config.exponential_base**attempt), config.max_delay)

    if config.jitter:
        # Add jitter: ±25% of the calculated delay
        jitter_amount = delay * 0.25
        delay += random.uniform(-jitter_amount, jitter_amount)  # nosec B311

    return max(0, delay)


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable based on exception type.

    Args:
        error: Exception to check

    Returns:
        True if the error should be retried

    Examples:
        - RetryableAPIError (5xx, network errors) → True
        - PermanentAPIError (4xx, auth failures) → False
        - APIRateLimitError → False (handled by rate limiter)
    """
    # Don't retry rate limit errors (handled by rate limiter)
    if isinstance(error, APIRateLimitError):
        return False

    # Retry errors explicitly marked as retryable
    if isinstance(error, RetryableAPIError):
        return True

    # Don't retry permanent errors (auth, 404, etc.)
    if isinstance(error, PermanentAPIError):
        return False

    # Retry general connection/timeout errors
    return isinstance(error, ConnectionError | TimeoutError)


def with_retry(config: RetryConfig | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add retry logic with exponential backoff to a function.

    Args:
        config: Retry configuration (uses defaults if None)

    Returns:
        Decorated function with retry logic

    Example:
        >>> @with_retry(RetryConfig(max_retries=3))
        ... def fetch_data():
        ...     return api.get("/data")
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Operation succeeded after {attempt} retries: {func.__name__}",
                            extra={"function": func.__name__, "attempts": attempt},
                        )
                    return result
                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if not is_retryable_error(e):
                        logger.debug(
                            f"Non-retryable error in {func.__name__}: {e}",
                            extra={"function": func.__name__, "error": str(e)},
                        )
                        raise

                    # If this was the last attempt, raise
                    if attempt >= config.max_retries:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for {func.__name__}",
                            exc_info=True,
                            extra={
                                "function": func.__name__,
                                "max_retries": config.max_retries,
                            },
                        )
                        raise

                    # Calculate delay and wait
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Retrying {func.__name__} after error: {e}. "
                        f"Attempt {attempt + 1}/{config.max_retries}, "
                        f"waiting {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": config.max_retries,
                            "delay": delay,
                            "error": str(e),
                        },
                    )
                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Retry logic failed unexpectedly for {func.__name__}")

        return wrapper

    return decorator


class RetryableOperation:
    """
    Context manager for retryable operations.

    Provides more granular control over retry behavior within a code block.

    Example:
        >>> with RetryableOperation(config=RetryConfig(max_retries=3)) as retry:
        ...     for attempt in retry:
        ...         try:
        ...             result = api.call()
        ...             break
        ...         except Exception as e:
        ...             retry.record_failure(e)
    """

    def __init__(self, config: RetryConfig | None = None):
        """
        Initialize retryable operation.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_error: Exception | None = None

    def __enter__(self) -> "RetryableOperation":
        """Enter retry context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit retry context."""
        return False

    def __iter__(self) -> "RetryableOperation":
        """Make this iterable for loop usage."""
        self.attempt = 0
        return self

    def __next__(self) -> int:
        """
        Get next retry attempt.

        Returns:
            Current attempt number

        Raises:
            StopIteration: When max retries exceeded
        """
        if self.attempt > self.config.max_retries:
            if self.last_error:
                logger.error(
                    f"Max retries ({self.config.max_retries}) exceeded",
                    exc_info=True,
                    extra={"max_retries": self.config.max_retries},
                )
                raise self.last_error
            raise StopIteration

        current = self.attempt
        self.attempt += 1
        return current

    def record_failure(self, error: Exception) -> None:
        """
        Record a failure and wait before next retry.

        Args:
            error: Exception that occurred
        """
        self.last_error = error

        if not is_retryable_error(error):
            logger.debug(f"Non-retryable error: {error}")
            raise error

        if self.attempt <= self.config.max_retries:
            delay = calculate_delay(self.attempt - 1, self.config)
            logger.warning(
                f"Operation failed, retrying. Attempt {self.attempt}/{self.config.max_retries}, "
                f"waiting {delay:.2f}s. Error: {error}",
                extra={
                    "attempt": self.attempt,
                    "max_retries": self.config.max_retries,
                    "delay": delay,
                    "error": str(error),
                },
            )
            time.sleep(delay)
