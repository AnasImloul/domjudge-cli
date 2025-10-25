"""Telemetry and metrics collection for observability.

This module provides telemetry infrastructure for tracking operations,
measuring performance, and monitoring system health. Supports both
structured logging and Prometheus-style metrics.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from dom.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """
    A single metric measurement.

    Attributes:
        name: Metric name (e.g., "api.request.duration")
        value: Metric value
        unit: Unit of measurement (e.g., "seconds", "count")
        tags: Additional tags for filtering/grouping
        timestamp: When the metric was recorded
    """

    name: str
    value: float
    unit: str = "count"
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


class MetricsCollector:
    """
    Collects and exports metrics for observability.

    Provides a simple interface for tracking operations, measuring durations,
    and recording custom metrics. Metrics can be exported in Prometheus format
    or as structured logs.

    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.increment("api.requests", tags={"endpoint": "/contests"})
        >>> with metrics.timer("api.request.duration", tags={"endpoint": "/contests"}):
        ...     # Make API call
        ...     pass
    """

    def __init__(self, enable_export: bool = True):
        """
        Initialize metrics collector.

        Args:
            enable_export: If True, log metrics for export
        """
        self.enable_export = enable_export
        self._metrics: list[Metric] = []

    def increment(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            value: Amount to increment by
            tags: Optional tags for grouping
        """
        metric = Metric(name=name, value=value, unit="count", tags=tags or {})
        self._record(metric)

    def gauge(
        self, name: str, value: float, unit: str = "count", tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a gauge metric (point-in-time measurement).

        Args:
            name: Metric name
            value: Gauge value
            unit: Unit of measurement
            tags: Optional tags for grouping
        """
        metric = Metric(name=name, value=value, unit=unit, tags=tags or {})
        self._record(metric)

    def histogram(
        self, name: str, value: float, unit: str = "seconds", tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a histogram metric (for distributions).

        Args:
            name: Metric name
            value: Measured value
            unit: Unit of measurement
            tags: Optional tags for grouping
        """
        metric = Metric(name=name, value=value, unit=unit, tags=tags or {})
        self._record(metric)

    @contextmanager
    def timer(self, name: str, unit: str = "seconds", tags: dict[str, str] | None = None):
        """
        Context manager for timing operations.

        Args:
            name: Metric name
            unit: Unit of measurement
            tags: Optional tags for grouping

        Example:
            >>> with metrics.timer("operation.duration"):
            ...     # Timed operation
            ...     pass
        """
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.histogram(name, duration, unit=unit, tags=tags)

    def _record(self, metric: Metric) -> None:
        """
        Record a metric.

        Args:
            metric: Metric to record
        """
        self._metrics.append(metric)

        if self.enable_export:
            # Log metric for export
            logger.info(
                f"METRIC: {metric.name}",
                extra={
                    "metric_name": metric.name,
                    "metric_value": metric.value,
                    "metric_unit": metric.unit,
                    "metric_tags": metric.tags,
                    "metric_timestamp": metric.timestamp,
                },
            )

    def get_metrics(self) -> list[Metric]:
        """Get all recorded metrics."""
        return self._metrics.copy()

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string

        Example output:
            # HELP api_requests_total Total API requests
            # TYPE api_requests_total counter
            api_requests_total{endpoint="/contests"} 42

            # HELP api_request_duration_seconds API request duration
            # TYPE api_request_duration_seconds histogram
            api_request_duration_seconds{endpoint="/contests"} 0.123
        """
        lines = []

        # Group metrics by name
        metrics_by_name: dict[str, list[Metric]] = {}
        for metric in self._metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric)

        # Format each metric group
        for name, metrics in metrics_by_name.items():
            # Sanitize name for Prometheus (replace dots with underscores)
            prom_name = name.replace(".", "_")

            # Determine metric type from unit
            if metrics[0].unit == "count":
                metric_type = "counter"
            elif metrics[0].unit in ["seconds", "milliseconds", "bytes"]:
                metric_type = "histogram"
            else:
                metric_type = "gauge"

            # Add HELP and TYPE comments
            lines.append(f"# HELP {prom_name} {name}")
            lines.append(f"# TYPE {prom_name} {metric_type}")

            # Add metric values
            for metric in metrics:
                if metric.tags:
                    tags_str = ",".join([f'{k}="{v}"' for k, v in sorted(metric.tags.items())])
                    lines.append(f"{prom_name}{{{tags_str}}} {metric.value}")
                else:
                    lines.append(f"{prom_name} {metric.value}")

            lines.append("")  # Blank line between metrics

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all recorded metrics."""
        self._metrics.clear()


# Global metrics collector instance
_global_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _global_metrics


# Convenience functions for common operations
def track_operation(operation_name: str, tags: dict[str, str] | None = None):
    """
    Decorator to track operation metrics.

    Args:
        operation_name: Name of the operation
        tags: Optional tags

    Example:
        >>> @track_operation("contest.apply", tags={"source": "cli"})
        ... def apply_contest(config):
        ...     # Operation logic
        ...     pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()

            # Track invocation
            metrics.increment(f"{operation_name}.invocations", tags=tags)

            # Track duration and success/failure
            with metrics.timer(f"{operation_name}.duration", tags=tags):
                try:
                    result = func(*args, **kwargs)
                    metrics.increment(f"{operation_name}.success", tags=tags)
                    return result
                except Exception as e:
                    metrics.increment(
                        f"{operation_name}.failures",
                        tags={**(tags or {}), "error_type": type(e).__name__},
                    )
                    raise

        return wrapper

    return decorator
