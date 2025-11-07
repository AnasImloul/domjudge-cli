"""Plan infrastructure changes operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.state import InfraStateComparator
from dom.logging_config import console, get_logger
from dom.types.config.processed import InfraConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class AnalyzeInfraChangesStep(ExecutableStep):
    """Step to analyze and display infrastructure changes."""

    def __init__(self, config: InfraConfig):
        super().__init__("analyze", "Analyze infrastructure changes")
        self.config = config

    def execute(self, _context: OperationContext) -> dict[str, Any]:
        """
        Analyze infrastructure changes.

        Returns:
            Dictionary with change analysis results
        """
        comparator = InfraStateComparator()
        change_set = comparator.compare(self.config)

        return {"change_set": change_set}


class DisplayInfraChangesStep(ExecutableStep):
    """Step to display infrastructure changes in a user-friendly format."""

    def __init__(self, analyze_step: AnalyzeInfraChangesStep):
        super().__init__("display", "Display planned changes")
        self.analyze_step = analyze_step
        self._changes_data: dict[str, Any] | None = None

    def execute(self, context: OperationContext) -> None:
        """Display the infrastructure changes that would be applied."""
        # Execute analysis step if not already done
        if self._changes_data is None:
            self._changes_data = self.analyze_step.execute(context)

        # Get changes from analysis
        change_set = self._changes_data.get("change_set")

        if not change_set:
            console.print("\n[dim]No infrastructure state found.[/dim]\n")
            return

        console.print("\n[bold]Planned Infrastructure Changes:[/bold]\n")

        # Display summary
        console.print(f"  {change_set.summary()}\n")

        # Display warnings for unsafe changes
        if change_set.requires_restart:
            console.print(
                "  [yellow]⚠ WARNING:[/yellow] This change requires full infrastructure restart"
            )
            console.print("  [yellow]⚠ This will cause downtime for running contests![/yellow]\n")

        # Display details
        if change_set.old_config:
            console.print("  [bold]Current state:[/bold]")
            console.print(f"    Port:       {change_set.old_config.port}")
            console.print(f"    Judgehosts: {change_set.old_config.judges}")
            console.print()

        console.print("  [bold]Desired state:[/bold]")
        console.print(f"    Port:       {change_set.new_config.port}")
        console.print(f"    Judgehosts: {change_set.new_config.judges}")
        console.print()

        # Recommendations
        if change_set.is_safe_live_change:
            console.print(
                "  [green]✓ This change is safe to apply to running infrastructure[/green]\n"
            )
        elif change_set.requires_restart:
            console.print("  [red]Recommendation:[/red]")
            console.print("    1. Notify participants of downtime")
            console.print("    2. Pause or finish active contests")
            console.print("    3. Run: dom infra destroy --confirm")
            console.print("    4. Run: dom infra apply")
            console.print("    5. Reconfigure contests if needed\n")


# ============================================================================
# Operation
# ============================================================================


class PlanInfraChangesOperation(SteppedOperation[dict[str, Any]]):
    """Plan infrastructure changes without applying them."""

    def __init__(self, config: InfraConfig):
        """
        Initialize plan operation.

        Args:
            config: Infrastructure configuration
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Plan infrastructure configuration changes"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate prerequisites."""
        # No prerequisites for planning
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for planning changes."""
        analyze_step = AnalyzeInfraChangesStep(self.config)
        return [
            analyze_step,
            DisplayInfraChangesStep(analyze_step),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[dict[str, Any]]:
        """Build final result."""
        changes_data = step_results.get("analyze", {})
        change_set = changes_data.get("change_set")

        if not change_set:
            return OperationResult.success(
                changes_data,
                "No infrastructure state found",
            )

        safe_str = "safe" if change_set.is_safe_live_change else "requires restart"

        return OperationResult.success(
            changes_data,
            f"Infrastructure change: {change_set.change_type.value} ({safe_str})",
        )
