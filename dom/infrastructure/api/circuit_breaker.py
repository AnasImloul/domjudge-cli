"""Circuit breaker pattern for preventing cascade failures.

This module implements a circuit breaker to fail fast when a service
is experiencing issues, preventing unnecessary requests and allowing
time for recovery.
"""

import time
from collections.abc import Callable
from enum import Enum
from threading import Lock
from typing import TypeVar

from dom.exceptions import APIError
from dom.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(APIError):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker configuration.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open state)
            success_threshold: Number of consecutive successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold


class CircuitBreaker:
    """
    Circuit breaker implementation.

    Prevents cascade failures by failing fast when a service is unhealthy.
    Automatically transitions between CLOSED -> OPEN -> HALF_OPEN -> CLOSED states.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, reject all requests immediately
        - HALF_OPEN: Testing recovery, allow limited requests

    Example:
        >>> breaker = CircuitBreaker("api-service")
        >>> with breaker:
        ...     result = api.call()
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._lock = Lock()

        logger.info(
            f"Circuit breaker '{name}' initialized",
            extra={
                "circuit_breaker": name,
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            },
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_failure_time = time.time()
        logger.warning(
            f"Circuit breaker '{self.name}' opened after {self._failure_count} failures",
            extra={
                "circuit_breaker": self.name,
                "state": "open",
                "failure_count": self._failure_count,
            },
        )

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        logger.info(
            f"Circuit breaker '{self.name}' entering half-open state (testing recovery)",
            extra={"circuit_breaker": self.name, "state": "half_open"},
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info(
            f"Circuit breaker '{self.name}' closed (service recovered)",
            extra={"circuit_breaker": self.name, "state": "closed"},
        )

    def record_success(self) -> None:
        """Record a successful operation."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}' success in half-open: "
                    f"{self._success_count}/{self.config.success_threshold}",
                    extra={
                        "circuit_breaker": self.name,
                        "success_count": self._success_count,
                        "success_threshold": self.config.success_threshold,
                    },
                )

                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    def record_failure(self, error: Exception) -> None:
        """
        Record a failed operation.

        Args:
            error: Exception that occurred
        """
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open state -> back to open
                logger.warning(
                    f"Circuit breaker '{self.name}' failed in half-open state, reopening",
                    extra={"circuit_breaker": self.name, "error": str(error)},
                )
                self._transition_to_open()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}' failure: "
                    f"{self._failure_count}/{self.config.failure_threshold}",
                    extra={
                        "circuit_breaker": self.name,
                        "failure_count": self._failure_count,
                        "failure_threshold": self.config.failure_threshold,
                        "error": str(error),
                    },
                )

                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to_open()

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:  # type: ignore[misc]
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._transition_to_half_open()

            # Reject if still open
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Service unavailable, try again in "
                    f"{self.config.recovery_timeout}s"
                )

        # Execute the call outside the lock
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    def __enter__(self) -> "CircuitBreaker":
        """Enter circuit breaker context."""
        with self._lock:
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._transition_to_half_open()

            if self._state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is open. Service unavailable."
                )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore[no-untyped-def]
        """Exit circuit breaker context."""
        if exc_type is None:
            self.record_success()
        elif exc_type is not CircuitBreakerError:
            self.record_failure(exc_val)
        return False

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._transition_to_closed()
            logger.info(
                f"Circuit breaker '{self.name}' manually reset",
                extra={"circuit_breaker": self.name},
            )
