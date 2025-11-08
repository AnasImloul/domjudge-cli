"""Verify problemset operation."""

from pathlib import Path
from typing import Any

from dom.core.config.loaders import load_contest_config, load_infrastructure_config
from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.problem.verify import verify_problemset
from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig, InfraConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class LoadContestForVerifyStep(ExecutableStep):
    """Step to load contest for verification."""

    def __init__(self, config_path: Path | None, contest_name: str) -> None:
        super().__init__("load_contest", "Load contest configuration")
        self.config_path = config_path
        self.contest_name = contest_name

    def execute(self, context: OperationContext) -> ContestConfig:
        """Load and return the contest."""
        return load_contest_config(self.config_path, self.contest_name, context.secrets)


class LoadInfraForVerifyStep(ExecutableStep):
    """Step to load infrastructure configuration for verification."""

    def __init__(self, infra_config_path: Path | None) -> None:
        super().__init__("load_infra", "Load infrastructure configuration")
        self.infra_config_path = infra_config_path

    def execute(self, _context: OperationContext) -> InfraConfig:
        """Load and return infrastructure config."""
        return load_infrastructure_config(self.infra_config_path)


class RunVerificationStep(ExecutableStep):
    """Step to run problemset verification."""

    def __init__(self) -> None:
        super().__init__("verify", "Verify problemset")

    def execute(self, _context: OperationContext) -> None:
        """Run verification - will be done in _build_result with access to loaded data."""
        return None


# ============================================================================
# Operation
# ============================================================================


class VerifyProblemsetOperation(SteppedOperation[None]):
    """Verify a contest's problemset."""

    def __init__(
        self, config_path: Path | None, contest_name: str, infra_config_path: Path | None = None
    ) -> None:
        """
        Initialize problemset verification operation.

        Args:
            config_path: Path to configuration file
            contest_name: Name of the contest to verify
            infra_config_path: Optional path to infrastructure config
        """
        self.config_path = config_path
        self.contest_name = contest_name
        self.infra_config_path = infra_config_path

    def describe(self) -> str:
        """Describe what this operation does."""
        return f"Verify problemset for contest '{self.contest_name}'"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate verification prerequisites."""
        errors = []
        if self.config_path and not self.config_path.exists():
            errors.append(f"Configuration file not found: {self.config_path}")
        if self.infra_config_path and not self.infra_config_path.exists():
            errors.append(f"Infrastructure config file not found: {self.infra_config_path}")
        return errors

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for verifying problemset."""
        return [
            LoadContestForVerifyStep(self.config_path, self.contest_name),
            LoadInfraForVerifyStep(self.infra_config_path),
            RunVerificationStep(),
        ]

    def _build_result(
        self, step_results: dict[str, Any], context: OperationContext
    ) -> OperationResult[None]:
        """Build final result and run verification."""
        contest = step_results.get("load_contest")
        infra_config = step_results.get("load_infra")

        if contest is None:
            return OperationResult.failure(
                ValueError("Contest loading failed"), "Failed to load contest"
            )

        if infra_config is None:
            return OperationResult.failure(
                ValueError("Infrastructure loading failed"), "Failed to load infrastructure config"
            )

        # Run verification
        verify_problemset(
            infra=infra_config,
            contest=contest,
            secrets=context.secrets,
        )

        return OperationResult.success(None, f"Verified {len(contest.problems)} problems")
