"""Load a single contest's configuration from disk."""

from pathlib import Path

from dom.core.config.loaders import load_contest_config
from dom.core.operations.framework import Context, operation
from dom.types.config.processed import ContestConfig


def _summary(contest: ContestConfig) -> str:
    return (
        f"Loaded '{contest.shortname}' • "
        f"{len(contest.problems)} problems • {len(contest.teams)} teams"
    )


@operation("Load contest configuration", summary=_summary)
def load_contest_config_op(ctx: Context, path: Path | None, contest_name: str) -> ContestConfig:
    if path is not None and not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    return load_contest_config(path, contest_name, ctx.secrets)
