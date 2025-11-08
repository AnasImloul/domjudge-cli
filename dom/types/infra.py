"""Infrastructure runtime state models.

This module contains models for infrastructure status and state,
not configuration models.
"""

from enum import Enum
from typing import Any


class ServiceStatus(str, Enum):
    """Service status enum."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    MISSING = "missing"


class InfrastructureStatus:
    """Container for infrastructure status information."""

    def __init__(self) -> None:
        self.docker_available: bool = False
        self.docker_error: str | None = None
        self.services: dict[str, ServiceStatus] = {}
        self.service_details: dict[str, dict[str, Any]] = {}

    def is_healthy(self) -> bool:
        """Check if all critical services are healthy."""
        if not self.docker_available:
            return False

        critical_services = ["domserver", "mariadb"]
        for service in critical_services:
            if self.services.get(service) != ServiceStatus.HEALTHY:
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert status to dictionary for JSON output."""
        return {
            "overall_status": "healthy" if self.is_healthy() else "unhealthy",
            "docker_available": self.docker_available,
            "docker_error": self.docker_error,
            "services": {name: status.value for name, status in self.services.items()},
            "details": self.service_details,
        }


__all__ = ["InfrastructureStatus", "ServiceStatus"]
