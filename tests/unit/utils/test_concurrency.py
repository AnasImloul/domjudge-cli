"""Tests for bounded executor and structured concurrency."""

import time

import pytest

from dom.utils.concurrency import BoundedExecutor


def test_bounded_executor_basic():
    """Test basic bounded executor functionality."""

    def simple_task(x):
        return x * 2

    with BoundedExecutor(max_workers=2, max_concurrent=2) as executor:
        results = list(executor.map(simple_task, [1, 2, 3, 4, 5]))

    # Results MUST be in order
    assert results == [2, 4, 6, 8, 10]


def test_bounded_executor_maintains_order_with_variable_timing():
    """Test that executor maintains order even when tasks complete in different order."""

    def variable_timing_task(x):
        # Make later items complete faster to test ordering
        sleep_time = (5 - x) * 0.01  # Item 5 finishes first, item 1 finishes last
        time.sleep(sleep_time)
        return x * 10

    with BoundedExecutor(max_workers=5, max_concurrent=5) as executor:
        results = list(executor.map(variable_timing_task, [1, 2, 3, 4, 5]))

    # MUST maintain input order despite reverse completion order
    assert results == [10, 20, 30, 40, 50]


def test_bounded_executor_limits_concurrency():
    """Test that bounded executor enforces concurrency limits."""
    active_tasks = {"count": 0, "max": 0}
    lock = __import__("threading").Lock()

    def track_concurrency(x):
        with lock:
            active_tasks["count"] += 1
            active_tasks["max"] = max(active_tasks["max"], active_tasks["count"])
        time.sleep(0.05)  # Simulate work
        with lock:
            active_tasks["count"] -= 1
        return x

    max_concurrent = 3
    with BoundedExecutor(max_workers=10, max_concurrent=max_concurrent) as executor:
        list(executor.map(track_concurrency, range(10)))

    # Should never exceed max_concurrent
    assert active_tasks["max"] <= max_concurrent


def test_bounded_executor_stop_on_error():
    """Test that executor stops on first error when requested."""

    def failing_task(x):
        if x == 3:
            raise ValueError("Task 3 failed")
        return x

    with BoundedExecutor(max_workers=5, max_concurrent=5) as executor:
        with pytest.raises(ValueError):
            list(executor.map(failing_task, range(10), stop_on_error=True))


def test_bounded_executor_order_preserved_with_large_dataset():
    """Test order preservation with larger dataset."""

    def process(x):
        # Random-ish processing time based on value
        time.sleep(0.001 * (x % 3))
        return x**2

    input_data = list(range(50))
    expected = [x**2 for x in input_data]

    with BoundedExecutor(max_workers=10, max_concurrent=5) as executor:
        results = list(executor.map(process, input_data))

    # Must maintain exact order
    assert results == expected


def test_bounded_executor_shutdown():
    """Test that executor properly shuts down."""
    executor = BoundedExecutor(max_workers=2, max_concurrent=2)

    def simple_task(x):
        return x * 2

    # Use executor - results MUST be in order
    results = list(executor.map(simple_task, [1, 2, 3]))
    assert results == [2, 4, 6]

    # Shutdown
    executor.shutdown(wait=True)

    # Should not be able to submit after shutdown
    with pytest.raises(RuntimeError):
        executor.submit(simple_task, 1)


def test_bounded_executor_empty_input():
    """Test that executor handles empty input correctly."""
    with BoundedExecutor(max_workers=2, max_concurrent=2) as executor:
        results = list(executor.map(lambda x: x * 2, []))

    assert results == []


def test_bounded_executor_single_item():
    """Test that executor handles single item correctly."""
    with BoundedExecutor(max_workers=2, max_concurrent=2) as executor:
        results = list(executor.map(lambda x: x * 2, [5]))

    assert results == [10]
