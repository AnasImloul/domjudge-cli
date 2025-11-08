"""Load single contest configuration operation."""

from pathlib import Path
from typing import Any

from dom.core.config.loaders import load_contest_config
from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class LoadSingleContestStep(ExecutableStep):
    """Step to load a single contest configuration."""

    def __init__(self, config_path: Path | None, contest_name: str) -> None:
        super().__init__("load", "Load contest configuration")
        self.config_path = config_path
        self.contest_name = contest_name

    def execute(self, context: OperationContext) -> ContestConfig:
        """Load and return the contest."""
        return load_contest_config(self.config_path, self.contest_name, context.secrets)


class ValidateSingleContestStep(ExecutableStep):
    """Step to validate single contest configuration."""

    def __init__(self) -> None:
        super().__init__("validate", "Validate contest configuration")

    def execute(self, _context: OperationContext) -> None:
        """Validate contest - already done in load step."""
        return None


# ============================================================================
# Operation
# ============================================================================


class LoadContestConfigOperation(SteppedOperation[ContestConfig]):
    """Load a single contest configuration."""

    def __init__(self, config_path: Path | None, contest_name: str) -> None:
        """
        Initialize single contest loading operation.

        Args:
            config_path: Path to configuration file
            contest_name: Contest short name
        """
        self.config_path = config_path
        self.contest_name = contest_name

    def describe(self) -> str:
        """Describe what this operation does."""
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load contest '{self.contest_name}' from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate that config file exists if path provided."""
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for loading a single contest."""
        return [
            LoadSingleContestStep(self.config_path, self.contest_name),
            ValidateSingleContestStep(),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[ContestConfig]:
        """Build final result from step results."""
        contest = step_results.get("load")
        if contest is None:
            return OperationResult.failure(
                ValueError("Contest loading failed"), "Failed to load contest configuration"
            )

        return OperationResult.success(
            contest,
            f"Loaded '{contest.shortname}' • {len(contest.problems)} problems • {len(contest.teams)} teams",
        )
