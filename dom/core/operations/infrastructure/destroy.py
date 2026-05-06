"""Destroy infrastructure operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.service import InfraService
from dom.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class DestroyInfrastructureStep(ExecutableStep):
    def __init__(self, remove_volumes: bool):
        label = (
            "Stop containers and remove volumes (PERMANENT)"
            if remove_volumes
            else "Stop all containers"
        )
        super().__init__("destroy", label)
        self.remove_volumes = remove_volumes

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).destroy(remove_volumes=self.remove_volumes)


# ============================================================================
# Operation
# ============================================================================


class DestroyInfrastructureOperation(SteppedOperation[None]):
    """Destroy all infrastructure components."""

    def __init__(self, remove_volumes: bool = False):
        self.remove_volumes = remove_volumes

    def describe(self) -> str:
        return "Destroy all infrastructure and platform components"

    def define_steps(self) -> list[ExecutableStep]:
        return [DestroyInfrastructureStep(self.remove_volumes)]

    def _build_result(
        self,
        _step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        if self.remove_volumes:
            return OperationResult.success(
                None, "All containers stopped • Volumes deleted permanently"
            )
        return OperationResult.success(None, "All containers stopped • Volumes preserved")
