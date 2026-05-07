"""CLI-side renderers for contest plan/apply output.

Operations and services return structured data; this module renders it.
Keeping presentation here means the core layers stay free of console
concerns.
"""

from typing import Any

from dom.core.services.contest.apply import ContestApplyResult
from dom.core.services.contest.changes import ChangeType
from dom.logging_config import console


def render_planned_changes(changes: list[dict[str, Any]]) -> None:
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


def render_apply_warnings(results: list[ContestApplyResult]) -> None:
    """Surface field deltas that could not be applied via the API."""
    affected = [r for r in results if r.skipped_field_changes]
    if not affected:
        return

    for result in affected:
        changed_fields = ", ".join(fc.field for fc in result.skipped_field_changes)
        console.print(f"\n[yellow]⚠ Contest '{result.contest_shortname}' already exists[/yellow]")
        console.print(f"[yellow]  Changed fields detected: {changed_fields}[/yellow]")
        console.print("[yellow]  → DOMjudge API does not support updating contests[/yellow]")
        console.print(
            "[yellow]  → Please update manually in DOMjudge web UI (Jury > Contests)[/yellow]\n"
        )
