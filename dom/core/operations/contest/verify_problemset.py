"""Verify a contest's problemset against the platform."""

from pathlib import Path

from dom.core.config.loaders import load_contest_config, load_infrastructure_config
from dom.core.operations.framework import Context, operation
from dom.core.services.problem.verify import verify_problemset
from dom.infrastructure.api.factory import APIClientFactory
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
    if config_path is not None and not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    if infra_config_path is not None and not infra_config_path.exists():
        raise FileNotFoundError(f"Infrastructure config file not found: {infra_config_path}")

    contest = load_contest_config(config_path, contest_name, ctx.secrets)
    infra = load_infrastructure_config(infra_config_path)
    client = APIClientFactory().create_admin_client(infra, ctx.secrets)
    verify_problemset(client=client, contest=contest, secrets=ctx.secrets)
    return contest
