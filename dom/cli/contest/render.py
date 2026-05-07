"""CLI-side renderers for contest plan/apply output.

Operations and services return structured data; this module renders it.
Keeping presentation here means the core layers stay free of console
concerns.
"""

from typing import Any

from dom import ui
from dom.core.services.contest.apply import ContestApplyResult
from dom.core.services.contest.changes import ChangeType, ContestChangeSet


def format_contest_change_summary(change_set: ContestChangeSet) -> str:
    """Render a :class:`ContestChangeSet` as a Rich-markup-decorated line."""
    change_type, shortname, parts = change_set.summary_parts()
    if change_type == ChangeType.CREATE:
        return f"[green]CREATE[/green] contest '{shortname}'"
    if not parts:
        return f"[dim]NO CHANGES[/dim] for contest '{shortname}'"
    return f"[yellow]UPDATE[/yellow] contest '{shortname}': {', '.join(parts)}"


def render_planned_changes(changes: list[dict[str, Any]]) -> None:
    if not changes:
        ui.blank()
        ui.hint("No changes detected.")
        ui.blank()
        return

    ui.blank()
    ui.write("Planned Changes:", style="bold")
    ui.blank()

    any_field_changes = False
    any_resource_changes = False
    any_creates = False

    for item in changes:
        change_set = item["change_set"]

        if change_set.change_type == ChangeType.CREATE:
            any_creates = True

        ui.info(f"  {format_contest_change_summary(change_set)}")

        if change_set.field_changes:
            any_field_changes = True
            ui.warn("    ⚠ Contest field changes (cannot be applied via API):")
            for field_change in change_set.field_changes:
                ui.info(f"      • {field_change}")

        for resource_change in change_set.resource_changes:
            if not resource_change.has_changes:
                continue
            any_resource_changes = True
            ui.info(f"    • {resource_change}")
            if resource_change.to_add and len(resource_change.to_add) <= 10:
                for item_name in resource_change.to_add:
                    ui.info(f"      + {item_name}")
            elif resource_change.to_add:
                ui.info(f"      + {len(resource_change.to_add)} items (showing first 10):")
                for item_name in resource_change.to_add[:10]:
                    ui.info(f"      + {item_name}")

        ui.blank()

    if any_field_changes:
        ui.warn("⚠ DOMjudge API Limitation:")
        ui.warn("  Contest field changes CANNOT be applied via API.")
        ui.warn("  → Please update manually in DOMjudge web UI (Jury > Contests)")
        ui.blank()

    if any_creates or any_resource_changes:
        ui.success("✓ Changes CAN be applied by 'dom contest apply'")
        ui.blank()

    if not any_field_changes and not any_resource_changes and not any_creates:
        ui.success("✓ All contests are up to date")
        ui.blank()


def render_apply_warnings(results: list[ContestApplyResult]) -> None:
    """Surface field deltas that could not be applied via the API."""
    affected = [r for r in results if r.skipped_field_changes]
    if not affected:
        return

    for result in affected:
        changed_fields = ", ".join(fc.field for fc in result.skipped_field_changes)
        ui.blank()
        ui.warn(f"⚠ Contest '{result.contest_shortname}' already exists")
        ui.warn(f"  Changed fields detected: {changed_fields}")
        ui.warn("  → DOMjudge API does not support updating contests")
        ui.warn("  → Please update manually in DOMjudge web UI (Jury > Contests)")
        ui.blank()
