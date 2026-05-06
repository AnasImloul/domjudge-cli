"""Plan infrastructure changes operation."""

from dom.core.operations.base import OperationContext, SimpleOperation
from dom.core.services.infra.state import InfraChangeSet, InfraStateComparator
from dom.logging_config import console, get_logger
from dom.types.infra import InfraConfig

logger = get_logger(__name__)


class PlanInfraChangesOperation(SimpleOperation[InfraChangeSet | None]):
    """Plan infrastructure changes without applying them."""

    def __init__(self, config: InfraConfig):
        self.config = config

    def describe(self) -> str:
        return "Plan infrastructure configuration changes"

    def run(self, _context: OperationContext) -> InfraChangeSet | None:
        change_set = InfraStateComparator().compare_infrastructure(self.config)
        _print_planned_changes(change_set)
        return change_set

    def _success_message(self, change_set: InfraChangeSet | None) -> str:
        if not change_set:
            return "No infrastructure state found"
        safe_str = "safe" if change_set.is_safe_live_change else "requires restart"
        return f"Infrastructure change: {change_set.change_type.value} ({safe_str})"


# ============================================================================
# Presenter
# ============================================================================


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
