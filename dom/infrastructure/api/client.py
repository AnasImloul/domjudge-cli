"""Base DOMjudge API client.

This module provides the core HTTP client with authentication, caching, and rate limiting.
Service classes build on top of this for specific resource types.
"""

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from dom.constants import DEFAULT_CACHE_TTL, DEFAULT_RATE_BURST, DEFAULT_RATE_LIMIT
from dom.exceptions import APIAuthenticationError, APIError, APINotFoundError
from dom.infrastructure.api.cache import TTLCache
from dom.infrastructure.api.rate_limiter import RateLimiter
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
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username=username, password=password)

        # Initialize cache and rate limiter
        self.cache = TTLCache(default_ttl=cache_ttl) if enable_cache else None
        self.rate_limiter = RateLimiter(rate=rate_limit, burst=rate_burst)

        logger.info(f"Initialized DOMjudge API client for {base_url}")

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
            APIAuthenticationError: For 401/403 errors
            APINotFoundError: For 404 errors
            APIError: For other HTTP errors
        """
        if response.status_code in {401, 403}:
            logger.error(f"Authentication failed: {response.status_code}")
            raise APIAuthenticationError(f"Authentication failed: {response.text}")
        elif response.status_code == 404:
            logger.warning(f"Resource not found: {response.url}")
            raise APINotFoundError(f"Resource not found: {response.text}")
        else:
            logger.error(f"API error {response.status_code}: {response.text}")
            raise APIError(f"API request failed: {response.status_code} - {response.text}")

    def get(
        self, path: str, cache_key: str | None = None, cache_ttl: int | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Perform GET request with caching.

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
        # Check cache
        if cache_key and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached  # type: ignore[no-any-return]

        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        response = self.session.get(self.url(path), **kwargs)
        if not response.ok:
            self.handle_response_error(response)

        data = response.json()

        # Store in cache
        if cache_key and self.cache:
            self.cache.set(cache_key, data, ttl=cache_ttl)
            logger.debug(f"Cached response for {cache_key}")

        return data  # type: ignore[no-any-return]

    def post(self, path: str, invalidate_cache: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Perform POST request.

        Args:
            path: API path
            invalidate_cache: Cache key to invalidate after successful request
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If request fails
        """
        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        response = self.session.post(self.url(path), **kwargs)
        if not response.ok:
            self.handle_response_error(response)

        # Invalidate cache
        if invalidate_cache and self.cache:
            self.cache.invalidate(invalidate_cache)

        return response.json()  # type: ignore[no-any-return]

    def put(self, path: str, invalidate_cache: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Perform PUT request.

        Args:
            path: API path
            invalidate_cache: Cache key to invalidate after successful request
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If request fails
        """
        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        response = self.session.put(self.url(path), **kwargs)
        if not response.ok:
            self.handle_response_error(response)

        # Invalidate cache
        if invalidate_cache and self.cache:
            self.cache.invalidate(invalidate_cache)

        return response.json()  # type: ignore[no-any-return]

    def delete(self, path: str, invalidate_cache: str | None = None, **kwargs) -> None:
        """
        Perform DELETE request.

        Args:
            path: API path
            invalidate_cache: Cache key to invalidate after successful request
            **kwargs: Additional arguments to pass to requests

        Raises:
            APIError: If request fails
        """
        # Rate limit
        self.rate_limiter.acquire()

        # Make request
        response = self.session.delete(self.url(path), **kwargs)
        if not response.ok:
            self.handle_response_error(response)

        # Invalidate cache
        if invalidate_cache and self.cache:
            self.cache.invalidate(invalidate_cache)
