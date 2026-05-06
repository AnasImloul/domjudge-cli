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
    def __init__(self, config_path: Path | None):
        super().__init__("load", "Load configuration file")
        self.config_path = config_path

    def execute(self, _context: OperationContext) -> InfraConfig:
        return load_infrastructure_config(self.config_path)


# ============================================================================
# Operation
# ============================================================================


class LoadInfraConfigOperation(SteppedOperation[InfraConfig]):
    """Load infrastructure configuration from file."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path

    def describe(self) -> str:
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load infrastructure configuration from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        return [LoadInfraConfigFileStep(self.config_path)]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[InfraConfig]:
        config = step_results.get("load")
        if config is None:
            return OperationResult.failure(
                ValueError("Configuration loading failed"),
                "Failed to load infrastructure configuration",
            )
        return OperationResult.success(config, f"Port {config.port} • {config.judges} judgehost(s)")
