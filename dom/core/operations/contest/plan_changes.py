"""Plan contest changes operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.contest.state import ChangeType, ContestStateComparator
from dom.logging_config import console, get_logger
from dom.types.config.processed import DomConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class AnalyzeChangesStep(ExecutableStep):
    """Step to analyze and display what would change."""

    def __init__(self, config: DomConfig):
        super().__init__("analyze", "Analyze configuration changes")
        self.config = config

    def execute(self, context: OperationContext) -> dict[str, Any]:
        """
        Analyze changes for all contests.

        Returns:
            Dictionary with change analysis results
        """
        comparator = ContestStateComparator(self.config.infra, context.secrets)

        results = []

        for contest in self.config.contests:
            change_set = comparator.compare(contest)
            results.append(
                {
                    "shortname": contest.shortname,
                    "change_set": change_set,
                }
            )

        return {"changes": results}


class DisplayChangesStep(ExecutableStep):
    """Step to display changes in a user-friendly format."""

    def __init__(self, analyze_step: AnalyzeChangesStep):
        super().__init__("display", "Display planned changes")
        self.analyze_step = analyze_step
        self._changes_data: dict[str, Any] | None = None

    def execute(self, context: OperationContext) -> None:
        """Display the changes that would be applied."""
        # Execute analysis step if not already done
        if self._changes_data is None:
            self._changes_data = self.analyze_step.execute(context)

        # Get changes from analysis
        changes = self._changes_data.get("changes", [])

        if not changes:
            console.print("\n[dim]No changes detected.[/dim]\n")
            return

        console.print("\n[bold]Planned Changes:[/bold]\n")

        any_field_changes = False
        any_resource_changes = False
        any_creates = False

        for item in changes:
            change_set = item["change_set"]

            # Track if there are any creates
            if change_set.change_type == ChangeType.CREATE:
                any_creates = True

            # Display summary
            console.print(f"  {change_set.summary()}")

            # Display detailed field changes with warning
            if change_set.field_changes:
                any_field_changes = True
                console.print(
                    "    [yellow]⚠ Contest field changes (cannot be applied via API):[/yellow]"
                )
                for field_change in change_set.field_changes:
                    console.print(f"      • {field_change}")

            # Display resource changes
            for resource_change in change_set.resource_changes:
                if resource_change.has_changes:
                    any_resource_changes = True
                    console.print(f"    • {resource_change}")
                    # Show details of what's being added
                    if resource_change.to_add and len(resource_change.to_add) <= 10:
                        for item_name in resource_change.to_add:
                            console.print(f"      + {item_name}")
                    elif resource_change.to_add:
                        console.print(
                            f"      + {len(resource_change.to_add)} items (showing first 10):"
                        )
                        for item_name in resource_change.to_add[:10]:
                            console.print(f"      + {item_name}")

            console.print()

        # Summary with clear explanation
        if any_field_changes:
            console.print("[yellow]⚠ DOMjudge API Limitation:[/yellow]")
            console.print("[yellow]  Contest field changes CANNOT be applied via API.[/yellow]")
            console.print(
                "[yellow]  → Please update manually in DOMjudge web UI (Jury > Contests)[/yellow]\n"
            )

        if any_creates or any_resource_changes:
            console.print("[green]✓ Changes CAN be applied by 'dom contest apply'[/green]\n")

        if not any_field_changes and not any_resource_changes and not any_creates:
            console.print("[green]✓ All contests are up to date[/green]\n")


# ============================================================================
# Operation
# ============================================================================


class PlanContestChangesOperation(SteppedOperation[dict[str, Any]]):
    """Plan contest changes without applying them."""

    def __init__(self, config: DomConfig):
        """
        Initialize plan operation.

        Args:
            config: Complete DOMjudge configuration
        """
        self.config = config

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Plan contest configuration changes"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate prerequisites."""
        # No prerequisites for planning
        return []

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for planning changes."""
        analyze_step = AnalyzeChangesStep(self.config)
        return [
            analyze_step,
            DisplayChangesStep(analyze_step),
        ]

    def _build_result(
        self,
        step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[dict[str, Any]]:
        """Build final result."""
        changes_data = step_results.get("analyze", {})
        changes = changes_data.get("changes", [])

        total_changes = sum(1 for item in changes if item["change_set"].has_changes)

        return OperationResult.success(
            changes_data,
            f"Analyzed {len(changes)} contest(s) • {total_changes} with changes",
        )
