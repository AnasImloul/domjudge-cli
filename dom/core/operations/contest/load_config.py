"""Load contest configuration from disk."""

from pathlib import Path

from dom.core.config.loaders import load_config
from dom.core.operations.framework import Context, operation
from dom.types.config.processed import DomConfig


def _summary(config: DomConfig) -> str:
    if len(config.contests) == 1:
        c = config.contests[0]
        return f"Loaded '{c.shortname}' • {len(c.problems)} problems • {len(c.teams)} teams"
    details = [f"{c.shortname}: {len(c.problems)}p/{len(c.teams)}t" for c in config.contests]
    return f"Loaded {len(config.contests)} contests ({', '.join(details)})"


@operation("Load configuration", summary=_summary)
def load_config_op(ctx: Context, path: Path | None = None) -> DomConfig:
    return load_config(path, ctx.secrets)
