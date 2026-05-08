"""Base DOMjudge API client.

Provides the core HTTP client with authentication, response caching, and
retry. Service classes build on top of this for specific resource types.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, TypeVar

import requests
from requests.auth import HTTPBasicAuth

from dom.constants import DEFAULT_CACHE_TTL
from dom.exceptions import (
    APIAuthenticationError,
    APIError,
    APINetworkError,
    APINotFoundError,
    APIRateLimitError,
    APIServerError,
)
from dom.infrastructure.api.cache import TTLCache
from dom.infrastructure.api.retry import RetryConfig, with_retry
from dom.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class DomJudgeClient:
    """
    Base HTTP client for DOMjudge API.

    Provides core functionality:
    - HTTP request handling with authentication
    - Response caching with TTL
    - Retry with exponential backoff
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
        enable_retry: bool = True,
        retry_config: RetryConfig | None = None,
    ):
        """
        Initialize the DOMjudge API client.

        Args:
            base_url: Base URL of the DOMjudge instance
            username: API username
            password: API password
            enable_cache: Enable response caching (default: True)
            cache_ttl: Cache time-to-live in seconds
            enable_retry: Enable retry with exponential backoff (default: True)
            retry_config: Custom retry configuration
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username=username, password=password)
        self.timeout = (10, 30)  # (connect timeout, read timeout)

        self.cache = TTLCache(default_ttl=cache_ttl) if enable_cache else None

        self.enable_retry = enable_retry
        self.retry_config = retry_config or RetryConfig()

        logger.info(
            f"Initialized DOMjudge API client for {base_url}",
            extra={
                "base_url": base_url,
                "enable_cache": enable_cache,
                "enable_retry": enable_retry,
            },
        )

    def url(self, path: str) -> str:
        """Construct a full URL from a path."""
        return f"{self.base_url}{path}"

    def handle_response_error(self, response: requests.Response) -> None:
        """
        Handle HTTP error responses with appropriate exceptions.

        Raises:
            APIAuthenticationError: For 401/403 errors (permanent)
            APINotFoundError: For 404 errors (permanent)
            APIRateLimitError: For 429 errors (retryable, honors Retry-After)
            APIServerError: For 5xx errors (retryable)
            APIError: For other HTTP errors
        """
        status = response.status_code

        if status in {401, 403}:
            logger.error(f"Authentication failed: {status}")
            raise APIAuthenticationError(
                f"Authentication failed: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        elif status == 404:
            logger.warning(f"Resource not found: {response.url}")
            raise APINotFoundError(
                f"Resource not found: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        elif status == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            logger.warning(
                f"Rate limited (429); Retry-After={retry_after}",
                extra={"retry_after": retry_after},
            )
            raise APIRateLimitError(
                f"Rate limited: {response.text}",
                status_code=status,
                response_body=response.text,
                retry_after=retry_after,
            )

        elif 500 <= status < 600:
            logger.error(f"Server error {status}: {response.text}")
            raise APIServerError(
                f"Server error: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        elif 400 <= status < 500:
            logger.error(f"Client error {status}: {response.text}")
            raise APIError(
                f"Client error: {response.text}",
                status_code=status,
                response_body=response.text,
            )

        else:
            logger.error(f"Unexpected API error {status}: {response.text}")
            raise APIError(
                f"API request failed: {status} - {response.text}",
                status_code=status,
                response_body=response.text,
            )

    def _retry(self, call: Callable[[], T]) -> T:
        """Apply retry decoration if enabled, then invoke."""
        if self.enable_retry:
            return with_retry(self.retry_config)(call)()
        return call()

    def _get_internal(
        self, path: str, cache_key: str | None = None, cache_ttl: int | None = None, **kwargs
    ) -> dict[str, Any]:
        """Internal GET implementation without retry."""
        if cache_key and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached  # type: ignore[no-any-return]

        try:
            response = self.session.get(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            data = response.json()

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
        """Perform GET request with caching and retry."""
        return self._retry(lambda: self._get_internal(path, cache_key, cache_ttl, **kwargs))

    def _post_internal(
        self, path: str, invalidate_cache: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Internal POST implementation without retry."""
        try:
            response = self.session.post(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            if invalidate_cache and self.cache:
                self.cache.invalidate(invalidate_cache)

            return response.json()  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during POST {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def post(self, path: str, invalidate_cache: str | None = None, **kwargs) -> dict[str, Any]:
        """Perform POST request with retry."""
        return self._retry(lambda: self._post_internal(path, invalidate_cache, **kwargs))

    def _put_internal(
        self, path: str, invalidate_cache: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Internal PUT implementation without retry."""
        try:
            response = self.session.put(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            if invalidate_cache and self.cache:
                self.cache.invalidate(invalidate_cache)

            return response.json()  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during PUT {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def put(self, path: str, invalidate_cache: str | None = None, **kwargs) -> dict[str, Any]:
        """Perform PUT request with retry."""
        return self._retry(lambda: self._put_internal(path, invalidate_cache, **kwargs))

    def _delete_internal(self, path: str, invalidate_cache: str | None = None, **kwargs) -> None:
        """Internal DELETE implementation without retry."""
        try:
            response = self.session.delete(self.url(path), timeout=self.timeout, **kwargs)
            if not response.ok:
                self.handle_response_error(response)

            if invalidate_cache and self.cache:
                self.cache.invalidate(invalidate_cache)
        except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
            logger.error(f"Network error during DELETE {path}: {e}")
            raise APINetworkError(f"Network error: {e}") from e

    def delete(self, path: str, invalidate_cache: str | None = None, **kwargs) -> None:
        """Perform DELETE request with retry."""
        self._retry(lambda: self._delete_internal(path, invalidate_cache, **kwargs))


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header into seconds. Accepts integer-seconds or HTTP-date."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    now = datetime.now(timezone.utc) if target.tzinfo else datetime.now()
    return max(0.0, (target - now).total_seconds())
