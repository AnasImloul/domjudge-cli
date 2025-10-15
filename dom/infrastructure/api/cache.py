"""Simple TTL cache for API responses.

This module provides a time-based cache for API responses to reduce
unnecessary network requests.
"""

import time
from threading import Lock
from typing import Any

from dom.logging_config import get_logger

logger = get_logger(__name__)


class TTLCache:
    """
    Time-to-live cache for storing temporary data.

    Thread-safe cache that automatically expires entries after a specified TTL.
    """

    def __init__(self, default_ttl: int = 300):
        """
        Initialize the TTL cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        """
        Get a value from the cache if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]

            if time.time() > expiry:
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None

            logger.debug(f"Cache hit for key: {key}")
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl

        with self._lock:
            self._cache[key] = (value, expiry)
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")

    def invalidate(self, key: str) -> bool:
        """
        Remove a key from the cache.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Invalidated cache for key: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cleared all cache entries")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        with self._lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items() if current_time > expiry
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)
