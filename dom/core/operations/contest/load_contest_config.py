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
    def __init__(self, config_path: Path | None, contest_name: str):
        super().__init__("load", "Load contest configuration")
        self.config_path = config_path
        self.contest_name = contest_name

    def execute(self, context: OperationContext) -> ContestConfig:
        return load_contest_config(self.config_path, self.contest_name, context.secrets)


# ============================================================================
# Operation
# ============================================================================


class LoadContestConfigOperation(SteppedOperation[ContestConfig]):
    """Load a single contest configuration."""

    def __init__(self, config_path: Path | None, contest_name: str):
        self.config_path = config_path
        self.contest_name = contest_name

    def describe(self) -> str:
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load contest '{self.contest_name}' from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        return [LoadSingleContestStep(self.config_path, self.contest_name)]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[ContestConfig]:
        contest = step_results.get("load")
        if contest is None:
            return OperationResult.failure(
                ValueError("Contest loading failed"), "Failed to load contest configuration"
            )

        return OperationResult.success(
            contest,
            f"Loaded '{contest.shortname}' • {len(contest.problems)} problems • {len(contest.teams)} teams",
        )
