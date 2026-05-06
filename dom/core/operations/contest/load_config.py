"""Load configuration operation."""

from pathlib import Path
from typing import Any

from dom.core.config.loaders import load_config
from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.logging_config import get_logger
from dom.types.config.processed import DomConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class ParseConfigFileStep(ExecutableStep):
    def __init__(self, config_path: Path | None):
        super().__init__("parse", "Parse configuration file")
        self.config_path = config_path

    def execute(self, context: OperationContext) -> DomConfig:
        return load_config(self.config_path, context.secrets)


# ============================================================================
# Operation
# ============================================================================


class LoadConfigOperation(SteppedOperation[DomConfig]):
    """Load contest configuration from yaml file."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path

    def describe(self) -> str:
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load configuration from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        return [ParseConfigFileStep(self.config_path)]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[DomConfig]:
        config = step_results.get("parse")
        if config is None:
            return OperationResult.failure(
                ValueError("Configuration loading failed"), "Failed to load configuration"
            )

        if len(config.contests) == 1:
            contest = config.contests[0]
            message = f"Loaded '{contest.shortname}' • {len(contest.problems)} problems • {len(contest.teams)} teams"
        else:
            contest_details = [
                f"{c.shortname}: {len(c.problems)}p/{len(c.teams)}t" for c in config.contests
            ]
            message = f"Loaded {len(config.contests)} contests ({', '.join(contest_details)})"

        return OperationResult.success(config, message)
