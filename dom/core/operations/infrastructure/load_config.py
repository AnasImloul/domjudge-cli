"""Load infrastructure configuration operation."""

from pathlib import Path

from dom.core.config.loaders import load_infrastructure_config
from dom.core.operations.base import OperationContext, SimpleOperation
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig

logger = get_logger(__name__)


class LoadInfraConfigOperation(SimpleOperation[InfraConfig]):
    """Load infrastructure configuration from file."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path

    def describe(self) -> str:
        path_str = str(self.config_path) if self.config_path else "default location"
        return f"Load infrastructure configuration from {path_str}"

    def validate(self, _context: OperationContext) -> list[str]:
        if self.config_path and not self.config_path.exists():
            return [f"Configuration file not found: {self.config_path}"]
        return []

    def run(self, _context: OperationContext) -> InfraConfig:
        return load_infrastructure_config(self.config_path)

    def _success_message(self, config: InfraConfig) -> str:
        return f"Port {config.port} • {config.judges} judgehost(s)"
