"""Load configuration operation."""

from pathlib import Path

from dom.core.config.loaders import load_config
from dom.core.operations.base import OperationContext, SimpleOperation
from dom.logging_config import get_logger
from dom.types.config.processed import DomConfig

logger = get_logger(__name__)


class LoadConfigOperation(SimpleOperation[DomConfig]):
    """Load contest configuration from yaml file."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path

    def describe(self) -> str:
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load configuration from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def run(self, context: OperationContext) -> DomConfig:
        return load_config(self.config_path, context.secrets)

    def _success_message(self, config: DomConfig) -> str:
        if len(config.contests) == 1:
            contest = config.contests[0]
            return (
                f"Loaded '{contest.shortname}' • "
                f"{len(contest.problems)} problems • {len(contest.teams)} teams"
            )
        details = [f"{c.shortname}: {len(c.problems)}p/{len(c.teams)}t" for c in config.contests]
        return f"Loaded {len(config.contests)} contests ({', '.join(details)})"
