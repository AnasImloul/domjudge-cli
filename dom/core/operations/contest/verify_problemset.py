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
from dom.types.config.processed import ContestConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class VerifyProblemsetStep(ExecutableStep):
    def __init__(self, config_path: Path | None, contest_name: str, infra_config_path: Path | None):
        super().__init__("verify", "Verify problemset")
        self.config_path = config_path
        self.contest_name = contest_name
        self.infra_config_path = infra_config_path

    def execute(self, context: OperationContext) -> ContestConfig:
        contest = load_contest_config(self.config_path, self.contest_name, context.secrets)
        infra = load_infrastructure_config(self.infra_config_path)
        verify_problemset(infra=infra, contest=contest, secrets=context.secrets)
        return contest


# ============================================================================
# Operation
# ============================================================================


class VerifyProblemsetOperation(SteppedOperation[None]):
    """Verify a contest's problemset."""

    def __init__(
        self, config_path: Path | None, contest_name: str, infra_config_path: Path | None = None
    ):
        self.config_path = config_path
        self.contest_name = contest_name
        self.infra_config_path = infra_config_path

    def describe(self) -> str:
        return f"Verify problemset for contest '{self.contest_name}'"

    def validate(self, _context: OperationContext) -> list[str]:
        errors = []
        if self.config_path and not self.config_path.exists():
            errors.append(f"Configuration file not found: {self.config_path}")
        if self.infra_config_path and not self.infra_config_path.exists():
            errors.append(f"Infrastructure config file not found: {self.infra_config_path}")
        return errors

    def define_steps(self) -> list[ExecutableStep]:
        return [
            VerifyProblemsetStep(self.config_path, self.contest_name, self.infra_config_path),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        contest = step_results.get("verify")
        if contest is None:
            return OperationResult.failure(
                ValueError("Verification failed"), "Failed to verify problemset"
            )
        return OperationResult.success(None, f"Verified {len(contest.problems)} problems")
