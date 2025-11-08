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
    """Step to parse the configuration file."""

    def __init__(self, config_path: Path | None) -> None:
        super().__init__("parse", "Parse configuration file")
        self.config_path = config_path

    def execute(self, context: OperationContext) -> DomConfig:
        """Parse and return the configuration."""
        return load_config(self.config_path, context.secrets)


class LoadContestsStep(ExecutableStep):
    """Step to load contest data from config."""

    def __init__(self) -> None:
        super().__init__("load_contests", "Load contest data")

    def execute(self, _context: OperationContext) -> None:
        """Load contests - already done in parse step."""
        return None


class ValidateConfigStep(ExecutableStep):
    """Step to validate contest configuration."""

    def __init__(self) -> None:
        super().__init__("validate", "Validate configuration")

    def execute(self, _context: OperationContext) -> None:
        """Validate configuration - already done in parse step."""
        return None


# ============================================================================
# Operation
# ============================================================================


class LoadConfigOperation(SteppedOperation[DomConfig]):
    """Load contest configuration from yaml file."""

    def __init__(self, config_path: Path | None = None) -> None:
        """
        Initialize config loading operation.

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path

    def describe(self) -> str:
        """Describe what this operation does."""
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load configuration from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate that config file exists if path provided."""
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for loading configuration."""
        return [
            ParseConfigFileStep(self.config_path),
            LoadContestsStep(),
            ValidateConfigStep(),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[DomConfig]:
        """Build final result from step results."""
        config = step_results.get("parse")
        if config is None:
            return OperationResult.failure(
                ValueError("Configuration loading failed"), "Failed to load configuration"
            )

        # Provide per-contest breakdown to avoid overcounting shared resources
        if len(config.contests) == 1:
            contest = config.contests[0]
            message = f"Loaded '{contest.shortname}' • {len(contest.problems)} problems • {len(contest.teams)} teams"
        else:
            # Show per-contest breakdown
            contest_details = [
                f"{c.shortname}: {len(c.problems)}p/{len(c.teams)}t" for c in config.contests
            ]
            message = f"Loaded {len(config.contests)} contests ({', '.join(contest_details)})"

        return OperationResult.success(config, message)
