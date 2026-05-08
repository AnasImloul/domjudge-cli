"""Plan contest changes without applying them."""

from typing import Any

from dom.core.operations.framework import Context, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.contest.state import ContestStateComparator
from dom.types.config.processed import DomConfig


def _summary(changes: list[dict[str, Any]]) -> str:
    total = sum(1 for item in changes if item["change_set"].has_changes)
    return f"Analyzed {len(changes)} contest(s) • {total} with changes"


@operation("Plan contest changes", summary=_summary, show_progress=False)
def plan_contest_changes_op(ctx: Context, config: DomConfig) -> list[dict[str, Any]]:
    """Compute per-contest change sets. Rendering is the CLI's job."""
    client = wire_admin_api(config.infra, ctx.secrets)
    comparator = ContestStateComparator(client, ctx.secrets)
    return [
        {"shortname": contest.shortname, "change_set": comparator.compare_contest(contest)}
        for contest in config.contests
    ]
