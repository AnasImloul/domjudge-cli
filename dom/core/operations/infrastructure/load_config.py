"""Load infrastructure configuration operation."""

from pathlib import Path
from typing import Any

from dom.core.config.loaders import load_infrastructure_config
from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class LoadInfraConfigFileStep(ExecutableStep):
    """Step to load infrastructure configuration from file."""

    def __init__(self, config_path: Path | None):
        super().__init__("load", "Load configuration file")
        self.config_path = config_path

    def execute(self, _context: OperationContext) -> InfraConfig:
        """Load the infrastructure configuration."""
        return load_infrastructure_config(self.config_path)


class ValidateInfraConfigStep(ExecutableStep):
    """Step to validate infrastructure configuration schema."""

    def __init__(self):
        super().__init__("validate", "Validate configuration schema")

    def execute(self, _context: OperationContext) -> None:
        """Validate configuration - already done in load step."""
        return None


# ============================================================================
# Operation
# ============================================================================


class LoadInfraConfigOperation(SteppedOperation[InfraConfig]):
    """Load infrastructure configuration from file."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize infra config loading operation.

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path

    def describe(self) -> str:
        """Describe what this operation does."""
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load infrastructure configuration from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate that config file exists if path provided."""
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for loading infrastructure configuration."""
        return [
            LoadInfraConfigFileStep(self.config_path),
            ValidateInfraConfigStep(),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[InfraConfig]:
        """Build final result from step results."""
        config = step_results.get("load")
        if config is None:
            return OperationResult.failure(
                ValueError("Configuration loading failed"),
                "Failed to load infrastructure configuration",
            )
        # Provide useful information about what was loaded
        return OperationResult.success(
            config,
            f"Port {config.port} • {config.judges} judgehost(s)",
        )
