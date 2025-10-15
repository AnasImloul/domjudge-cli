"""Declarative operations for initialization."""

from dom.core.services.init import callback as init_service_callback
from dom.logging_config import get_logger

from .base import Operation, OperationContext, OperationResult

logger = get_logger(__name__)


class InitializeProjectOperation(Operation[None]):
    """Initialize DomJudge CLI project with configuration files."""

    def __init__(self, overwrite: bool = False):
        """
        Initialize project initialization operation.

        Args:
            overwrite: Overwrite existing files if True
        """
        self.overwrite = overwrite

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Initialize DomJudge CLI project"

    def execute(self, context: OperationContext) -> OperationResult[None]:  # noqa: ARG002
        """Execute project initialization."""
        try:
            init_service_callback(overwrite=self.overwrite)
            return OperationResult.success(None, "Project initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize project: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to initialize project: {e}")
