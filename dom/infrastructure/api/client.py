"""Base DOMjudge API client.

This module provides the core HTTP client with authentication, caching, and rate limiting.
Service classes build on top of this for specific resource types.
"""

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from dom.constants import DEFAULT_CACHE_TTL, DEFAULT_RATE_BURST, DEFAULT_RATE_LIMIT
from dom.exceptions import (
    APIAuthenticationError,
    APIError,
    APINetworkError,
    APINotFoundError,
    APIServerError,
)
from dom.infrastructure.api.cache import TTLCache
from dom.infrastructure.api.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from dom.infrastructure.api.rate_limiter import RateLimiter
from dom.infrastructure.api.retry import RetryConfig, with_retry
from dom.logging_config import get_logger

logger = get_logger(__name__)


class DomJudgeClient:
    """
    Base HTTP client for DOMjudge API.

    Provides core functionality:
    - HTTP request handling with authentication
    - Response caching with TTL
    - Rate limiting
    - Error handling and logging

    Service classes (ContestService, ProblemService, etc.) build on this client.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        enable_cache: bool = True,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        rate_burst: int = DEFAULT_RATE_BURST,
        enable_retry: bool = True,
        retry_config: RetryConfig | None = None,
        enable_circuit_breaker: bool = True,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        """
        Initialize the DOMjudge API client.

        Args:
            base_url: Base URL of the DOMjudge instance
            username: API username
            password: API password
            enable_cache: Enable response caching (default: True)
            cache_ttl: Cache time-to-live in seconds
            rate_limit: Requests per second limit
            rate_burst: Maximum burst size
            enable_retry: Enable retry with exponential backoff (default: True)
            retry_config: Custom retry configuration
            enable_circuit_breaker: Enable circuit breaker (default: True)
            circuit_breaker_config: Custom circuit breaker configuration
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username=username, password=password)
        # Set reasonable timeout (will be used in requests)
        self.timeout = (10, 30)  # (connect timeout, read timeout)

        # Initialize cache and rate limiter
        self.cache = TTLCache(default_ttl=cache_ttl) if enable_cache else None
        self.rate_limiter = RateLimiter(rate=rate_limit, burst=rate_burst)

        # Initialize retry and circuit breaker
        self.enable_retry = enable_retry
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = (
            CircuitBreaker(f"domjudge-{base_url}", circuit_breaker_config)
            if enable_circuit_breaker
            else None
        )

        logger.info(
            f"Initialized DOMjudge API client for {base_url}",
            extra={
                "base_url": base_url,
                "enable_cache": enable_cache,
                "enable_retry": enable_retry,
                "enable_circuit_breaker": enable_circuit_breaker,
            },
        )

    def url(self, path: str) -> str:
        """
        Construct full URL from path.

        Args:
            path: API path (e.g., "/api/v4/contests")

        Returns:
            Full URL
        """
        return f"{self.base_url}{path}"

    def handle_response_error(self, response: requests.Response) -> None:
        """
        Handle HTTP error responses with appropriate exceptions.

        Args:
            response: Response object from requests

        Raises:
            APIAuthenticationError: For 401/403 errors (permanent)
            APINotFoundError: For 404 errors (permanent)
            APIServerError: For 5xx errors (retryable)
            APIError: For other HTTP errors
        """
        status = response.status_code

        # Authentication errors (permanent)
        if status in {401, 403}:
            logger.error(f"Authentication failed: {status}")
            raise APIAuthenticationError(
                f"Authentication failed: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        # Not found (permanent)
        elif status == 404:
            logger.warning(f"Resource not found: {response.url}")
            raise APINotFoundError(
                f"Resource not found: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        # Server errors (retryable)
        elif 500 <= status < 600:
            logger.error(f"Server error {status}: {response.text}")
            raise APIServerError(
                f"Server error: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        # Other client errors (permanent)
        elif 400 <= status < 500:
            logger.error(f"Client error {status}: {response.text}")
            raise APIError(
                f"Client error: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        # Unknown error
        else:
            logger.error(f"Unexpected API error {status}: {response.text}")
            raise APIError(
                f"API request failed: {status} - {response.text}",
                status_code=status,
                response_body=response.text,
            )

    def _get_internal(
        self, path: str, cache_key: str | None = None, cache_ttl: int | None = None, **kwargs
    ) -> dict[str, Any]:
        """Internal GET implementation without retry/circuit breaker."""
        # Check cache
        if cache_key and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached  # type: ignore[no-any-return]

        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        try:
            response = self.session.get(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            data = response.json()

            # Store in cache
            if cache_key and self.cache:
                self.cache.set(cache_key, data, ttl=cache_ttl)
                logger.debug(f"Cached response for {cache_key}")

            return data  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during GET {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def get(
        self, path: str, cache_key: str | None = None, cache_ttl: int | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Perform GET request with caching, retry, and circuit breaker.

        Args:
            path: API path
            cache_key: Cache key (if None, no caching)
            cache_ttl: Override default cache TTL
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If request fails
        """

        def _call() -> dict[str, Any]:
            return self._get_internal(path, cache_key, cache_ttl, **kwargs)

        # Apply circuit breaker if enabled
        if self.circuit_breaker:
            cb = self.circuit_breaker  # Type narrowing

            def _call_with_cb() -> dict[str, Any]:
                return cb.call(_call)
        else:
            _call_with_cb = _call

        # Apply retry if enabled
        if self.enable_retry:
            decorated = with_retry(self.retry_config)(_call_with_cb)
            return decorated()
        else:
            return _call_with_cb()

    def _post_internal(
        self, path: str, invalidate_cache: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Internal POST implementation without retry/circuit breaker."""
        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        try:
            response = self.session.post(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            # Invalidate cache
            if invalidate_cache and self.cache:
                self.cache.invalidate(invalidate_cache)

            return response.json()  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during POST {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def post(self, path: str, invalidate_cache: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Perform POST request with retry and circuit breaker.

        Args:
            path: API path
            invalidate_cache: Cache key to invalidate after successful request
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If request fails
        """

        def _call() -> dict[str, Any]:
            return self._post_internal(path, invalidate_cache, **kwargs)

        # Apply circuit breaker if enabled
        if self.circuit_breaker:
            cb = self.circuit_breaker  # Type narrowing

            def _call_with_cb() -> dict[str, Any]:
                return cb.call(_call)
        else:
            _call_with_cb = _call

        # Apply retry if enabled
        if self.enable_retry:
            decorated = with_retry(self.retry_config)(_call_with_cb)
            return decorated()
        else:
            return _call_with_cb()

    def _put_internal(
        self, path: str, invalidate_cache: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Internal PUT implementation without retry/circuit breaker."""
        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        try:
            response = self.session.put(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            # Invalidate cache
            if invalidate_cache and self.cache:
                self.cache.invalidate(invalidate_cache)

            return response.json()  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during PUT {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def put(self, path: str, invalidate_cache: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Perform PUT request with retry and circuit breaker.

        Args:
            path: API path
            invalidate_cache: Cache key to invalidate after successful request
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If request fails
        """

        def _call() -> dict[str, Any]:
            return self._put_internal(path, invalidate_cache, **kwargs)

        # Apply circuit breaker if enabled
        if self.circuit_breaker:
            cb = self.circuit_breaker  # Type narrowing

            def _call_with_cb() -> dict[str, Any]:
                return cb.call(_call)
        else:
            _call_with_cb = _call

        # Apply retry if enabled
        if self.enable_retry:
            decorated = with_retry(self.retry_config)(_call_with_cb)
            return decorated()
        else:
            return _call_with_cb()

    def _delete_internal(self, path: str, invalidate_cache: str | None = None, **kwargs) -> None:
        """Internal DELETE implementation without retry/circuit breaker."""
        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        try:
            response = self.session.delete(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            # Invalidate cache
            if invalidate_cache and self.cache:
                self.cache.invalidate(invalidate_cache)
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during DELETE {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def delete(self, path: str, invalidate_cache: str | None = None, **kwargs) -> None:
        """
        Perform DELETE request with retry and circuit breaker.

        Args:
            path: API path
            invalidate_cache: Cache key to invalidate after successful request
            **kwargs: Additional arguments to pass to requests

        Raises:
            APIError: If request fails
        """

        def _call() -> None:
            return self._delete_internal(path, invalidate_cache, **kwargs)

        # Apply circuit breaker if enabled
        if self.circuit_breaker:
            cb = self.circuit_breaker  # Type narrowing

            def _call_with_cb() -> None:
                return cb.call(_call)
        else:
            _call_with_cb = _call

        # Apply retry if enabled
        if self.enable_retry:
            decorated = with_retry(self.retry_config)(_call_with_cb)
            decorated()
        else:
            _call_with_cb()
