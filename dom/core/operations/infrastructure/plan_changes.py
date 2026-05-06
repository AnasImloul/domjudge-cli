"""Plan infrastructure changes without applying them."""

from dom.core.operations.framework import Context, operation
from dom.core.services.infra.state import InfraChangeSet, InfraStateComparator
from dom.logging_config import console
from dom.types.infra import InfraConfig


def _summary(change_set: InfraChangeSet | None) -> str:
    if not change_set:
        return "No infrastructure state found"
    safety = "safe" if change_set.is_safe_live_change else "requires restart"
    return f"Infrastructure change: {change_set.change_type.value} ({safety})"


@operation("Plan infrastructure changes", summary=_summary, show_progress=False)
def plan_infra_changes_op(_ctx: Context, config: InfraConfig) -> InfraChangeSet | None:
    change_set = InfraStateComparator().compare_infrastructure(config)
    _print_planned_changes(change_set)
    return change_set


# ---------------------------------------------------------------- presenter


def _print_planned_changes(change_set: InfraChangeSet | None) -> None:
    if not change_set:
        console.print("\n[dim]No infrastructure state found.[/dim]\n")
        return

    console.print("\n[bold]Planned Infrastructure Changes:[/bold]\n")
    console.print(f"  {change_set.summary()}\n")

    if change_set.requires_restart:
        console.print(
            "  [yellow]⚠ WARNING:[/yellow] This change requires full infrastructure restart"
        )
        console.print("  [yellow]⚠ This will cause downtime for running contests![/yellow]\n")

    if change_set.old_config:
        console.print("  [bold]Current state:[/bold]")
        console.print(f"    Port:       {change_set.old_config.port}")
        console.print(f"    Judgehosts: {change_set.old_config.judges}")
        console.print()

    console.print("  [bold]Desired state:[/bold]")
    console.print(f"    Port:       {change_set.new_config.port}")
    console.print(f"    Judgehosts: {change_set.new_config.judges}")
    console.print()

    if change_set.is_safe_live_change:
        console.print("  [green]✓ This change is safe to apply to running infrastructure[/green]\n")
    elif change_set.requires_restart:
        console.print("  [red]Recommendation:[/red]")
        console.print("    1. Notify participants of downtime")
        console.print("    2. Pause or finish active contests")
        console.print("    3. Run: dom infra destroy --confirm")
        console.print("    4. Run: dom infra apply")
        console.print("    5. Reconfigure contests if needed\n")
