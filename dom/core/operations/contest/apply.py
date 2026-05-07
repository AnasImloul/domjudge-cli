"""Apply contest configuration to the DOMjudge platform."""

from dom.core.operations.framework import Context, Step, Steps, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.contest.apply import ContestApplicationService
from dom.types.config.processed import DomConfig


def _summary(config: DomConfig) -> str:
    if len(config.contests) == 1:
        c = config.contests[0]
        return f"Applied '{c.shortname}' • {len(c.problems)} problems • {len(c.teams)} teams"
    details = [f"{c.shortname}: {len(c.problems)}p/{len(c.teams)}t" for c in config.contests]
    return f"Applied {len(config.contests)} contests ({', '.join(details)})"


def _apply_all(config: DomConfig, ctx: Context) -> None:
    """Wire an admin API client and push every contest through the service."""
    client = wire_admin_api(config.infra, ctx.secrets)
    service = ContestApplicationService(client, ctx.secrets)
    for contest in config.contests:
        service.apply_contest(contest)


@operation("Apply contests")
def apply_contests_op(ctx: Context, config: DomConfig) -> Steps:
    if not config.contests:
        raise ValueError("No contests in configuration")
    return Steps(
        steps=[
            Step(
                f"Push {len(config.contests)} contest(s) to platform",
                lambda: _apply_all(config, ctx),
            ),
        ],
        summary=_summary(config),
    )
