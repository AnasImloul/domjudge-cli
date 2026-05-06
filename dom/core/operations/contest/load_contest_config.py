"""Load single contest configuration operation."""

from pathlib import Path

from dom.core.config.loaders import load_contest_config
from dom.core.operations.base import OperationContext, SimpleOperation
from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig

logger = get_logger(__name__)


class LoadContestConfigOperation(SimpleOperation[ContestConfig]):
    """Load a single contest configuration."""

    def __init__(self, config_path: Path | None, contest_name: str):
        self.config_path = config_path
        self.contest_name = contest_name

    def describe(self) -> str:
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load contest '{self.contest_name}' from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def run(self, context: OperationContext) -> ContestConfig:
        return load_contest_config(self.config_path, self.contest_name, context.secrets)

    def _success_message(self, contest: ContestConfig) -> str:
        return (
            f"Loaded '{contest.shortname}' • "
            f"{len(contest.problems)} problems • {len(contest.teams)} teams"
        )
