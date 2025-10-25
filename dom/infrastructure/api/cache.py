"""Simple TTL cache for API responses with LRU eviction.

This module provides a time-based cache for API responses to reduce
unnecessary network requests, with size limits to prevent memory leaks.
"""

import time
from collections import OrderedDict
from threading import Lock
from typing import Any

from dom.logging_config import get_logger

logger = get_logger(__name__)


class TTLCache:
    """
    Time-to-live cache with LRU eviction for storing temporary data.

    Thread-safe cache that automatically expires entries after a specified TTL
    and enforces a maximum size using LRU (Least Recently Used) eviction.

    Attributes:
        default_ttl: Default time-to-live in seconds
        max_size: Maximum number of entries (None = unlimited)
    """

    def __init__(self, default_ttl: int = 300, max_size: int | None = 1000):
        """
        Initialize the TTL cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            max_size: Maximum number of entries before LRU eviction (default: 1000)
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        # Use OrderedDict for LRU behavior (maintains insertion order)
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        """
        Get a value from the cache if it exists and hasn't expired.

        Updates access time for LRU eviction policy.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]
            current_time = time.time()

            if current_time > expiry:
                # Expired, remove it atomically within the lock
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None

            # Move to end for LRU (mark as recently used)
            self._cache.move_to_end(key)

            logger.debug(f"Cache hit for key: {key}")
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Store a value in the cache with LRU eviction if at capacity.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl

        with self._lock:
            # If key exists, update and move to end
            if key in self._cache:
                self._cache[key] = (value, expiry)
                self._cache.move_to_end(key)
                logger.debug(f"Updated cached value for key: {key} (TTL: {ttl}s)")
                return

            # Check if we need to evict (before adding new entry)
            if self.max_size is not None and len(self._cache) >= self.max_size:
                # Evict oldest entry (first item in OrderedDict)
                evicted_key = next(iter(self._cache))
                del self._cache[evicted_key]
                logger.debug(
                    f"LRU eviction: removed '{evicted_key}' to make room",
                    extra={"evicted_key": evicted_key, "max_size": self.max_size},
                )

            # Add new entry
            self._cache[key] = (value, expiry)
            logger.debug(
                f"Cached value for key: {key} (TTL: {ttl}s, size: {len(self._cache)}/{self.max_size})"
            )

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

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, max_size, etc.)
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
            }
