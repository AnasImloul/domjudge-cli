"""Load infrastructure configuration from disk."""

from pathlib import Path

from dom.core.config.loaders import load_infrastructure_config
from dom.core.operations.framework import Context, operation
from dom.types.infra import InfraConfig


def _summary(config: InfraConfig) -> str:
    return f"Port {config.port} • {config.judges} judgehost(s)"


@operation("Load infrastructure configuration", summary=_summary)
def load_infra_config_op(_ctx: Context, path: Path | None = None) -> InfraConfig:
    if path is not None and not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    return load_infrastructure_config(path)
