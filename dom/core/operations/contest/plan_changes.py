"""Plan contest changes operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.contest.plan import ContestPlan, plan_contest_changes
from dom.logging_config import get_logger
from dom.types.config.processed import DomConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class AnalyzeChangesStep(ExecutableStep):
    """Step to analyze what changes will be made."""

    def __init__(self, config: DomConfig):
        super().__init__("analyze", "Analyze required changes")
        self.config = config

    def execute(self, context: OperationContext) -> ContestPlan:
        """Analyze and return the change plan."""
        return plan_contest_changes(self.config, context.secrets)


class CalculateImpactStep(ExecutableStep):
    """Step to calculate impact of changes."""

    def __init__(self):
        super().__init__("calculate_impact", "Calculate change impact")

    def execute(self, _context: OperationContext) -> None:
        """Calculate impact - already done in analyze step."""
        return None


# ============================================================================
# Operation
# ============================================================================


class PlanContestChangesOperation(SteppedOperation[str]):
    """Plan what changes will be made to contests without applying them."""

    def __init__(self, config: DomConfig):
        """
        Initialize contest planning operation.

        Args:
            config: Contest configuration to plan
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        count = len(self.config.contests)
        return f"Plan changes for {count} contest(s)"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate planning operation."""
        if not self.config.contests:
            return ["No contests in configuration"]
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for planning changes."""
        return [
            AnalyzeChangesStep(self.config),
            CalculateImpactStep(),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[str]:
        """Build final result from step results."""
        plan = step_results.get("analyze")
        if plan is None:
            return OperationResult.failure(ValueError("Planning failed"), "Failed to plan changes")

        # Format plan as string for display
        summary = (
            f"Planned changes:\n"
            f"  - Contests: {plan.contest_count}\n"
            f"  - Problems: {plan.total_problems}\n"
            f"  - Teams: {plan.total_teams}"
        )

        return OperationResult.success(
            summary, f"Planned changes for {len(self.config.contests)} contest(s)"
        )
