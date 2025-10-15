"""Tests for TTL cache."""

import time

from dom.infrastructure.api.cache import TTLCache


def test_cache_set_and_get():
    """Test basic cache set and get operations."""
    cache = TTLCache(default_ttl=10)

    cache.set("key1", "value1")
    value = cache.get("key1")

    assert value == "value1"


def test_cache_get_nonexistent():
    """Test getting a non-existent key returns None."""
    cache = TTLCache(default_ttl=10)
    value = cache.get("nonexistent")

    assert value is None


def test_cache_expiration():
    """Test that cache entries expire after TTL."""
    cache = TTLCache(default_ttl=1)  # 1 second TTL

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Wait for expiration
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_custom_ttl():
    """Test setting custom TTL for specific keys."""
    cache = TTLCache(default_ttl=10)

    cache.set("key1", "value1", ttl=1)  # 1 second TTL
    assert cache.get("key1") == "value1"

    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_invalidate():
    """Test cache invalidation."""
    cache = TTLCache(default_ttl=10)

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    result = cache.invalidate("key1")
    assert result is True
    assert cache.get("key1") is None

    # Invalidating non-existent key should return False
    result2 = cache.invalidate("key1")
    assert result2 is False


def test_cache_clear():
    """Test clearing all cache entries."""
    cache = TTLCache(default_ttl=10)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    cache.clear()

    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_cleanup_expired():
    """Test cleanup of expired entries."""
    cache = TTLCache(default_ttl=1)

    cache.set("key1", "value1")
    cache.set("key2", "value2", ttl=10)  # Won't expire

    time.sleep(1.1)

    # Manually cleanup expired entries
    removed = cache.cleanup_expired()

    assert removed == 1
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
