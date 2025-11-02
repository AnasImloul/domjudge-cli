"""Apply contests operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.contest.apply import apply_contests
from dom.logging_config import get_logger
from dom.types.config.processed import DomConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class ApplyAllContestsStep(ExecutableStep):
    """Step to apply all contests to DomJudge platform."""

    def __init__(self, config: DomConfig):
        super().__init__("apply", "Apply contests to platform")
        self.config = config

    def execute(self, context: OperationContext) -> None:
        """Apply all contests to the platform."""
        apply_contests(self.config, context.secrets)


# ============================================================================
# Operation
# ============================================================================


class ApplyContestsOperation(SteppedOperation[None]):
    """Apply contest configuration to DomJudge platform."""

    def __init__(self, config: DomConfig):
        """
        Initialize contest application operation.

        Args:
            config: Contest configuration to apply
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        count = len(self.config.contests)
        return f"Apply {count} contest(s) to DomJudge platform"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate before applying contests."""
        if not self.config.contests:
            return ["No contests in configuration"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for applying contests."""
        return [
            ApplyAllContestsStep(self.config),
        ]

    def _build_result(
        self,
        _step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        """Build final result from step results."""
        # Provide per-contest breakdown to avoid overcounting shared resources
        if len(self.config.contests) == 1:
            contest = self.config.contests[0]
            message = f"Applied '{contest.shortname}' • {len(contest.problems)} problems • {len(contest.teams)} teams"
        else:
            # Show per-contest breakdown
            contest_details = [
                f"{c.shortname}: {len(c.problems)}p/{len(c.teams)}t" for c in self.config.contests
            ]
            message = f"Applied {len(self.config.contests)} contests ({', '.join(contest_details)})"

        return OperationResult.success(None, message)
