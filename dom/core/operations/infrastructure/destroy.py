"""Destroy infrastructure operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.destroy import destroy_infra_and_platform
from dom.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class StopContainersStep(ExecutableStep):
    """Step to stop all infrastructure containers."""

    def __init__(self):
        super().__init__("stop_containers", "Stop all containers")

    def execute(self, context: OperationContext) -> dict[str, bool]:
        """Execute container stopping."""
        destroy_infra_and_platform(context.secrets, remove_volumes=False)
        return {"stopped": True}


class ConditionalRemoveVolumesStep(ExecutableStep):
    """Conditional step to remove volumes - skips if not needed."""

    def __init__(self, should_remove: bool):
        super().__init__("remove_volumes", "Remove all volumes (PERMANENT)")
        self._should_remove = should_remove

    def should_execute(self, _context: OperationContext) -> bool:
        """Only execute if volumes should be removed."""
        return self._should_remove

    def execute(self, context: OperationContext) -> dict[str, bool]:
        """Execute volume removal."""
        destroy_infra_and_platform(context.secrets, remove_volumes=True)
        return {"volumes_removed": True}


# ============================================================================
# Operation
# ============================================================================


class DestroyInfrastructureOperation(SteppedOperation[None]):
    """Destroy all infrastructure components."""

    def __init__(self, remove_volumes: bool = False):
        """
        Initialize infrastructure destruction operation.

        Args:
            remove_volumes: If True, delete volumes (PERMANENT DATA LOSS)
        """
        self.remove_volumes = remove_volumes

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Destroy all infrastructure and platform components"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate destruction operation."""
        # Could add validation to check if infrastructure exists
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for destroying infrastructure."""
        return [
            StopContainersStep(),
            ConditionalRemoveVolumesStep(self.remove_volumes),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        """Build final result with informative message."""
        volumes_removed = step_results.get("remove_volumes") is not None
        if volumes_removed:
            return OperationResult.success(
                None, "All containers stopped • Volumes deleted permanently"
            )
        else:
            return OperationResult.success(None, "All containers stopped • Volumes preserved")
