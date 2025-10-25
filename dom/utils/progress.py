"""Enhanced progress tracking for CLI operations.

This module provides rich progress bars and JSON output support
for better user experience and automation integration.
"""

import json
import sys
from contextlib import contextmanager
from typing import Any

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from dom.logging_config import console, get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """
    Enhanced progress tracker with rich progress bars and JSON output.

    Supports both human-readable progress bars and machine-readable JSON output
    for automation integration.

    Example:
        >>> tracker = ProgressTracker(json_output=False)
        >>> with tracker.track("Deploying", total=10) as task:
        ...     for i in range(10):
        ...         tracker.update(task, advance=1, status=f"Step {i}")
    """

    def __init__(self, json_output: bool = False, show_percentage: bool = True):
        """
        Initialize progress tracker.

        Args:
            json_output: If True, output JSON instead of progress bars
            show_percentage: If True, show percentage complete in progress bars
        """
        self.json_output = json_output
        self.show_percentage = show_percentage
        self._progress: Progress | None = None
        self._json_events: list[dict[str, Any]] = []

    def _create_progress(self) -> Progress:
        """Create a rich Progress instance with custom columns."""
        columns = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
        ]

        if self.show_percentage:
            columns.append(TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))

        columns.extend(
            [
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                TextColumn("[dim]{task.fields[status]}"),
            ]
        )

        return Progress(*columns, console=console)

    @contextmanager
    def track(self, description: str, total: int | None = None):
        """
        Context manager for tracking a task.

        Args:
            description: Task description
            total: Total number of steps (None for indeterminate)

        Yields:
            Task ID for updating progress

        Example:
            >>> with tracker.track("Processing items", total=100) as task:
            ...     for i in range(100):
            ...         # Do work
            ...         tracker.update(task, advance=1)
        """
        if self.json_output:
            # JSON mode: emit start event
            event = {
                "type": "task_start",
                "description": description,
                "total": total,
                "timestamp": self._get_timestamp(),
            }
            self._emit_json(event)
            yield description  # Use description as task ID in JSON mode
        else:
            # Progress bar mode
            if self._progress is None:
                self._progress = self._create_progress()
                self._progress.start()

            task_id = self._progress.add_task(description, total=total, status="")
            try:
                yield task_id
            finally:
                # Mark as complete
                if total is not None and self._progress.tasks[task_id].completed < total:
                    self._progress.update(task_id, completed=total)

    def update(
        self,
        task_id: TaskID | str,
        advance: int = 0,
        completed: int | None = None,
        status: str = "",
    ) -> None:
        """
        Update progress for a task.

        Args:
            task_id: Task ID (from track context manager)
            advance: Number of steps to advance
            completed: Absolute completion value
            status: Current status message
        """
        if self.json_output:
            # JSON mode: emit progress event
            event = {
                "type": "task_progress",
                "task": str(task_id),
                "advance": advance,
                "completed": completed,
                "status": status,
                "timestamp": self._get_timestamp(),
            }
            self._emit_json(event)
        # Progress bar mode
        elif self._progress is not None:
            self._progress.update(task_id, advance=advance, completed=completed, status=status)

    def finish(self) -> None:
        """Finish progress tracking and cleanup."""
        if self.json_output:
            # Emit final summary
            event = {
                "type": "summary",
                "total_events": len(self._json_events),
                "timestamp": self._get_timestamp(),
            }
            self._emit_json(event)
        elif self._progress is not None:
            self._progress.stop()
            self._progress = None

    def _emit_json(self, event: dict[str, Any]) -> None:
        """
        Emit a JSON event.

        Args:
            event: Event dictionary to emit
        """
        self._json_events.append(event)
        # Write to stdout for automation tools
        print(json.dumps(event), file=sys.stdout, flush=True)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"

    def __enter__(self) -> "ProgressTracker":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore[no-untyped-def]
        """Exit context manager."""
        self.finish()
        return False


def format_json_output(data: dict[str, Any], pretty: bool = True) -> str:
    """
    Format data as JSON string.

    Args:
        data: Data to format
        pretty: If True, pretty-print with indentation

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(data, indent=2, sort_keys=True)
    else:
        return json.dumps(data, sort_keys=True)


def print_json(data: dict[str, Any], pretty: bool = True) -> None:
    """
    Print data as JSON to stdout.

    Args:
        data: Data to print
        pretty: If True, pretty-print with indentation
    """
    print(format_json_output(data, pretty=pretty))
