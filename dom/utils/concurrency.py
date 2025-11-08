"""Structured concurrency utilities for bounded parallel operations.

This module provides utilities to enforce concurrency limits using semaphores
and thread pools, preventing resource exhaustion from unbounded parallelism.
"""

import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Literal, TypeVar

from dom.constants import MAX_CONCURRENT_PROBLEM_OPERATIONS, MAX_CONCURRENT_TEAM_OPERATIONS
from dom.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class BoundedExecutor:
    """
    Thread pool executor with semaphore-based concurrency limiting.

    Enforces maximum concurrent operations using a semaphore, preventing
    unbounded thread creation and resource exhaustion.

    Example:
        >>> executor = BoundedExecutor(max_workers=10, max_concurrent=3)
        >>> results = executor.map(process_item, items)
    """

    def __init__(self, max_workers: int, max_concurrent: int | None = None) -> None:
        """
        Initialize bounded executor.

        Args:
            max_workers: Maximum number of worker threads
            max_concurrent: Maximum concurrent operations (defaults to max_workers)
        """
        self.max_workers = max_workers
        self.max_concurrent = max_concurrent or max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._semaphore = threading.Semaphore(self.max_concurrent)

        logger.info(
            f"Initialized BoundedExecutor: {max_workers} workers, "
            f"{self.max_concurrent} max concurrent",
            extra={"max_workers": max_workers, "max_concurrent": self.max_concurrent},
        )

    def submit(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> Future[T]:
        """
        Submit a task with concurrency limiting.

        Acquires semaphore before submission, releases after completion.

        Args:
            fn: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Future representing the task
        """

        def wrapped() -> T:
            try:
                return fn(*args, **kwargs)
            finally:
                self._semaphore.release()

        # Acquire semaphore before submitting
        self._semaphore.acquire()
        return self._executor.submit(wrapped)

    def map(
        self,
        fn: Callable[[T], R],
        iterable: Iterable[T],
        timeout: float | None = None,
        stop_on_error: bool = True,
    ) -> list[R]:
        """
        Map function over iterable with concurrency limiting.

        Results are returned in the same order as the input iterable, regardless
        of completion order. This guarantees deterministic output.

        Args:
            fn: Function to apply to each item
            iterable: Items to process
            timeout: Timeout per operation (None = no timeout)
            stop_on_error: If True, stop on first error; if False, collect all results

        Returns:
            List of results in the same order as input

        Raises:
            Exception: If stop_on_error=True and any operation fails
        """
        items = list(iterable)
        futures: dict[Future[R], int] = {}  # Map future to index
        results_with_index: list[tuple[int, R]] = []  # Store (index, result)
        errors: list[tuple[int, Exception]] = []

        logger.info(
            f"Processing {len(items)} items with {self.max_concurrent} max concurrent",
            extra={"items_count": len(items), "max_concurrent": self.max_concurrent},
        )

        # Submit all tasks with their indices
        for idx, item in enumerate(items):
            future = self.submit(fn, item)
            futures[future] = idx

        # Collect results as they complete
        for future in as_completed(futures, timeout=timeout):
            idx = futures[future]
            try:
                result = future.result()
                results_with_index.append((idx, result))
            except Exception as e:
                logger.error(
                    f"Task failed for item at index {idx}: {e}",
                    exc_info=True,
                    extra={"index": idx},
                )
                errors.append((idx, e))

                if stop_on_error:
                    # Cancel remaining futures
                    for remaining in futures:
                        if not remaining.done():
                            remaining.cancel()
                    raise

        if errors and not stop_on_error:
            logger.warning(
                f"Completed with {len(errors)} errors out of {len(items)} items",
                extra={"error_count": len(errors), "total_items": len(items)},
            )

        # Sort results by original index to maintain order
        results_with_index.sort(key=lambda x: x[0])
        return [result for _, result in results_with_index]

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """
        Shutdown the executor.

        Args:
            wait: If True, wait for all tasks to complete
            cancel_futures: If True, cancel pending futures (Python 3.9+)
        """
        try:
            self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
        except TypeError:
            # Python < 3.9 doesn't support cancel_futures
            self._executor.shutdown(wait=wait)

    def __enter__(self) -> "BoundedExecutor":
        """Enter context manager."""
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> Literal[False]:
        """Exit context manager."""
        self.shutdown(wait=True)
        return False


def get_team_executor() -> BoundedExecutor:
    """
    Get a bounded executor for team operations.

    Returns:
        Executor with MAX_CONCURRENT_TEAM_OPERATIONS limit
    """
    return BoundedExecutor(
        max_workers=MAX_CONCURRENT_TEAM_OPERATIONS * 2,  # Buffer for I/O waiting
        max_concurrent=MAX_CONCURRENT_TEAM_OPERATIONS,
    )


def get_problem_executor() -> BoundedExecutor:
    """
    Get a bounded executor for problem operations.

    Returns:
        Executor with MAX_CONCURRENT_PROBLEM_OPERATIONS limit
    """
    return BoundedExecutor(
        max_workers=MAX_CONCURRENT_PROBLEM_OPERATIONS * 2,  # Buffer for I/O waiting
        max_concurrent=MAX_CONCURRENT_PROBLEM_OPERATIONS,
    )
