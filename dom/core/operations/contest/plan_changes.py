"""Plan contest changes operation."""

from typing import Any

from dom.core.operations.base import OperationContext, SimpleOperation
from dom.core.services.contest.changes import ChangeType
from dom.core.services.contest.state import ContestStateComparator
from dom.infrastructure.api.factory import APIClientFactory
from dom.logging_config import console, get_logger
from dom.types.config.processed import DomConfig

logger = get_logger(__name__)


class PlanContestChangesOperation(SimpleOperation[list[dict[str, Any]]]):
    """Plan contest changes without applying them."""

    def __init__(self, config: DomConfig):
        self.config = config

    def describe(self) -> str:
        return "Plan contest configuration changes"

    def run(self, context: OperationContext) -> list[dict[str, Any]]:
        client = APIClientFactory().create_admin_client(self.config.infra, context.secrets)
        comparator = ContestStateComparator(client)
        changes = [
            {"shortname": contest.shortname, "change_set": comparator.compare_contest(contest)}
            for contest in self.config.contests
        ]
        _print_planned_changes(changes)
        return changes

    def _success_message(self, changes: list[dict[str, Any]]) -> str:
        total_changes = sum(1 for item in changes if item["change_set"].has_changes)
        return f"Analyzed {len(changes)} contest(s) • {total_changes} with changes"


# ============================================================================
# Presenter
# ============================================================================


def _print_planned_changes(changes: list[dict[str, Any]]) -> None:
    if not changes:
        console.print("\n[dim]No changes detected.[/dim]\n")
        return

    console.print("\n[bold]Planned Changes:[/bold]\n")

    any_field_changes = False
    any_resource_changes = False
    any_creates = False

    for item in changes:
        change_set = item["change_set"]

        if change_set.change_type == ChangeType.CREATE:
            any_creates = True

        console.print(f"  {change_set.summary()}")

        if change_set.field_changes:
            any_field_changes = True
            console.print(
                "    [yellow]⚠ Contest field changes (cannot be applied via API):[/yellow]"
            )
            for field_change in change_set.field_changes:
                console.print(f"      • {field_change}")

        for resource_change in change_set.resource_changes:
            if not resource_change.has_changes:
                continue
            any_resource_changes = True
            console.print(f"    • {resource_change}")
            if resource_change.to_add and len(resource_change.to_add) <= 10:
                for item_name in resource_change.to_add:
                    console.print(f"      + {item_name}")
            elif resource_change.to_add:
                console.print(f"      + {len(resource_change.to_add)} items (showing first 10):")
                for item_name in resource_change.to_add[:10]:
                    console.print(f"      + {item_name}")

        console.print()

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
