"""Plan infrastructure changes without applying them."""

from dom.core.operations.framework import Context, operation
from dom.core.services.infra.state import InfraChangeSet, InfraStateComparator
from dom.types.infra import InfraConfig


def _summary(change_set: InfraChangeSet | None) -> str:
    if not change_set:
        return "No infrastructure state found"
    safety = "safe" if change_set.is_safe_live_change else "requires restart"
    return f"Infrastructure change: {change_set.change_type.value} ({safety})"


@operation("Plan infrastructure changes", summary=_summary, show_progress=False)
def plan_infra_changes_op(_ctx: Context, config: InfraConfig) -> InfraChangeSet | None:
    """Compute the infrastructure change set. Rendering is the CLI's job."""
    return InfraStateComparator().compare_infrastructure(config)
