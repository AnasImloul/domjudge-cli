"""Verify a contest's problemset against the platform."""

from pathlib import Path

from dom.core.config.loaders import load_contest_config, load_infrastructure_config
from dom.core.operations.framework import Context, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.problem.verify import verify_problemset
from dom.types.config.processed import ContestConfig


def _summary(contest: ContestConfig) -> str:
    return f"Verified {len(contest.problems)} problems"


@operation("Verify problemset", summary=_summary, show_progress=False)
def verify_problemset_op(
    ctx: Context,
    config_path: Path | None,
    contest_name: str,
    infra_config_path: Path | None = None,
) -> ContestConfig:
    contest = load_contest_config(config_path, contest_name, ctx.secrets)
    infra = load_infrastructure_config(infra_config_path)
    client = wire_admin_api(infra, ctx.secrets)
    verify_problemset(client=client, contest=contest, secrets=ctx.secrets)
    return contest
