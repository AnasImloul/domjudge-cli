"""Plan contest changes without applying them."""

from dom.core.operations.framework import Context, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.contest.changes import ContestPlan, ContestPlanItem
from dom.core.services.contest.state import ContestStateComparator
from dom.types.config.processed import DomConfig


def _summary(plan: ContestPlan) -> str:
    return f"Analyzed {len(plan.items)} contest(s) • {plan.changed_count} with changes"


@operation("Plan contest changes", summary=_summary, show_progress=False)
def plan_contest_changes_op(ctx: Context, config: DomConfig) -> ContestPlan:
    """Compute per-contest change sets. Rendering is the CLI's job."""
    client = wire_admin_api(config.infra, ctx.secrets)
    comparator = ContestStateComparator(client, ctx.secrets)
    return ContestPlan(
        items=[
            ContestPlanItem(
                shortname=contest.shortname or "?",
                change_set=comparator.compare_contest(contest),
            )
            for contest in config.contests
        ]
    )
