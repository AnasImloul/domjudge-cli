from enum import Enum

from pydantic import BaseModel, SecretStr

from dom.utils.pydantic import InspectMixin


class InfraConfig(InspectMixin, BaseModel):
    port: int = 12345
    judges: int = 1
    password: SecretStr | None = None

    class Config:
        frozen = True


class ServiceStatus(str, Enum):
    """Service status enum."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    MISSING = "missing"


class InfrastructureStatus:
    """Container for infrastructure status information."""

    def __init__(self):
        self.docker_available: bool = False
        self.docker_error: str | None = None
        self.services: dict[str, ServiceStatus] = {}
        self.service_details: dict[str, dict] = {}

    def is_healthy(self) -> bool:
        """Check if all critical services are healthy."""
        if not self.docker_available:
            return False

        critical_services = ["domserver", "mariadb"]
        for service in critical_services:
            if self.services.get(service) != ServiceStatus.HEALTHY:
                return False

        return True

    def to_dict(self) -> dict:
        """Convert status to dictionary for JSON output."""
        return {
            "overall_status": "healthy" if self.is_healthy() else "unhealthy",
            "docker_available": self.docker_available,
            "docker_error": self.docker_error,
            "services": {name: status.value for name, status in self.services.items()},
            "details": self.service_details,
        }


__all__ = ["InfraConfig", "InfrastructureStatus", "ServiceStatus"]
