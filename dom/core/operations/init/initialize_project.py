"""Initialize project operation."""

from dom.core.operations.base import Operation, OperationContext, OperationResult
from dom.core.services.init import callback as init_service_callback
from dom.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Operation
# ============================================================================


class InitializeProjectOperation(Operation[None]):
    """Initialize DomJudge CLI project with configuration files."""

    def __init__(self, overwrite: bool = False) -> None:
        """
        Initialize project initialization operation.

        Args:
            overwrite: Overwrite existing files if True
        """
        self.overwrite = overwrite

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Initialize DomJudge CLI project"

    def execute(self, _context: OperationContext) -> OperationResult[None]:
        """Execute project initialization."""
        try:
            init_service_callback(overwrite=self.overwrite)
            return OperationResult.success(None, "Project initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize project: {e}", exc_info=True)
            return OperationResult.failure(e, f"Failed to initialize project: {e}")
