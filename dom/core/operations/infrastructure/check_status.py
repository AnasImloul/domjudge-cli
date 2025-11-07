"""Check infrastructure status operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.status import check_infrastructure_status
from dom.logging_config import get_logger
from dom.types.config.processed import InfraConfig
from dom.types.infra import InfrastructureStatus

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class CheckDockerStep(ExecutableStep):
    """Step to check Docker daemon availability."""

    def __init__(self):
        super().__init__("check_docker", "Check Docker daemon")

    def execute(self, _context: OperationContext) -> None:
        """Check Docker daemon - done in check_infrastructure_status."""
        return None


class CheckContainersStep(ExecutableStep):
    """Step to check container status."""

    def __init__(self, config: InfraConfig | None):
        super().__init__("check_containers", "Check container status")
        self.config = config

    def execute(self, _context: OperationContext) -> None:
        """Check container status - done in check_infrastructure_status."""
        return None


class CheckHealthStep(ExecutableStep):
    """Step to check service health."""

    def __init__(self, config: InfraConfig | None):
        super().__init__("check_health", "Check service health")
        self.config = config

    def execute(self, _context: OperationContext) -> InfrastructureStatus:
        """Check infrastructure health and return status."""
        return check_infrastructure_status(self.config)


# ============================================================================
# Operation
# ============================================================================


class CheckInfrastructureStatusOperation(SteppedOperation[InfrastructureStatus]):
    """Check the health status of infrastructure components."""

    def __init__(self, config: InfraConfig | None = None):
        """
        Initialize status check operation.

        Args:
            config: Optional infrastructure configuration for expected state
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Check infrastructure health status"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate status check operation."""
        # No prerequisites for checking status
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for checking infrastructure status."""
        return [
            CheckDockerStep(),
            CheckContainersStep(self.config),
            CheckHealthStep(self.config),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[InfrastructureStatus]:
        """Build final result from step results."""
        status = step_results.get("check_health")
        if status is None:
            return OperationResult.failure(
                ValueError("Status check failed"),
                "Failed to check infrastructure status",
            )
        message = (
            "Infrastructure is healthy" if status.is_healthy() else "Infrastructure has issues"
        )
        return OperationResult.success(status, message)
