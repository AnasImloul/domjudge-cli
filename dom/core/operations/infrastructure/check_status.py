"""Check infrastructure status operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.service import InfraService
from dom.logging_config import get_logger
from dom.types.infra import InfrastructureStatus

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class CheckInfraStatusStep(ExecutableStep):
    def __init__(self):
        super().__init__("check", "Check infrastructure status")

    def execute(self, context: OperationContext) -> InfrastructureStatus:
        return InfraService(context.secrets).check_status()


# ============================================================================
# Operation
# ============================================================================


class CheckInfrastructureStatusOperation(SteppedOperation[InfrastructureStatus]):
    """Check the health status of infrastructure components."""

    def describe(self) -> str:
        return "Check infrastructure health status"

    def define_steps(self) -> list[ExecutableStep]:
        return [CheckInfraStatusStep()]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[InfrastructureStatus]:
        status = step_results.get("check")
        if status is None:
            return OperationResult.failure(
                ValueError("Status check failed"),
                "Failed to check infrastructure status",
            )
        message = (
            "Infrastructure is healthy" if status.is_healthy() else "Infrastructure has issues"
        )
        return OperationResult.success(status, message)
