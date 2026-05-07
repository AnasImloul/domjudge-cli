"""Apply contest configuration to the DOMjudge platform."""

from dom.core.operations.framework import Context, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.contest.apply import ContestApplicationService, ContestApplyResult
from dom.core.services.contest.state import ContestStateComparator
from dom.core.services.problem.apply import ProblemService
from dom.core.services.team.apply import TeamService
from dom.types.config.processed import DomConfig


def _summary(results: list[ContestApplyResult]) -> str:
    if len(results) == 1:
        r = results[0]
        suffix = " (with skipped field changes)" if r.skipped_field_changes else ""
        return f"Applied '{r.contest_shortname}'{suffix}"
    skipped = sum(1 for r in results if r.skipped_field_changes)
    suffix = f" • {skipped} with skipped field changes" if skipped else ""
    return f"Applied {len(results)} contests{suffix}"


def _apply_all(config: DomConfig, ctx: Context) -> list[ContestApplyResult]:
    """Wire dependencies once, then apply every contest through the service."""
    client = wire_admin_api(config.infra, ctx.secrets)
    service = ContestApplicationService(
        client,
        ctx.secrets,
        problem_service=ProblemService(client),
        team_service=TeamService(client),
        state_comparator=ContestStateComparator(client),
    )
    return [service.apply_contest(contest) for contest in config.contests]


@operation("Apply contests", summary=_summary, show_progress=False)
def apply_contests_op(ctx: Context, config: DomConfig) -> list[ContestApplyResult]:
    if not config.contests:
        raise ValueError("No contests in configuration")
    return _apply_all(config, ctx)
