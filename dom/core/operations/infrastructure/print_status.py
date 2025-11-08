"""Print infrastructure status operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.status import (
    check_infrastructure_status,
    print_status_human_readable,
    print_status_json,
)
from dom.logging_config import get_logger
from dom.types.config.processed import InfraConfig
from dom.types.infra import InfrastructureStatus

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class CheckInfraStatusStep(ExecutableStep):
    """Step to check infrastructure status."""

    def __init__(self, config: InfraConfig | None) -> None:
        super().__init__("check", "Check infrastructure status")
        self.config = config

    def execute(self, _context: OperationContext) -> InfrastructureStatus:
        """Check and return infrastructure status."""
        return check_infrastructure_status(self.config)


class DisplayStatusStep(ExecutableStep):
    """Step to display infrastructure status."""

    def __init__(self, json_output: bool) -> None:
        super().__init__("display", "Display status information")
        self.json_output = json_output

    def execute(self, _context: OperationContext) -> None:
        """Display status - will be done in _build_result with access to status."""
        return None


# ============================================================================
# Operation
# ============================================================================


class PrintInfrastructureStatusOperation(SteppedOperation[None]):
    """Check and print infrastructure status."""

    def __init__(self, config: InfraConfig | None = None, json_output: bool = False) -> None:
        """
        Initialize status print operation.

        Args:
            config: Optional infrastructure configuration for expected state
            json_output: Output in JSON format if True
        """
        self.config = config
        self.json_output = json_output

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Check and display infrastructure status"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate status print operation."""
        # No prerequisites for checking status
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for checking and printing status."""
        return [
            CheckInfraStatusStep(self.config),
            DisplayStatusStep(self.json_output),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        """Build final result and print status."""
        status = step_results.get("check")
        if status is None:
            return OperationResult.failure(
                ValueError("Status check failed"),
                "Failed to check infrastructure status",
            )

        # Print status
        if self.json_output:
            print_status_json(status)
        else:
            print_status_human_readable(status)

        # Always return success - the status check itself succeeded
        message = (
            "Infrastructure is healthy" if status.is_healthy() else "Infrastructure is not healthy"
        )
        return OperationResult.success(None, message)
