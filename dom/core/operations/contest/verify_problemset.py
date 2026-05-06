"""Verify problemset operation."""

from pathlib import Path

from dom.core.config.loaders import load_contest_config, load_infrastructure_config
from dom.core.operations.base import OperationContext, SimpleOperation
from dom.core.services.problem.verify import verify_problemset
from dom.infrastructure.api.factory import APIClientFactory
from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig

logger = get_logger(__name__)


class VerifyProblemsetOperation(SimpleOperation[ContestConfig]):
    """Verify a contest's problemset."""

    def __init__(
        self, config_path: Path | None, contest_name: str, infra_config_path: Path | None = None
    ):
        self.config_path = config_path
        self.contest_name = contest_name
        self.infra_config_path = infra_config_path

    def describe(self) -> str:
        return f"Verify problemset for contest '{self.contest_name}'"

    def validate(self, _context: OperationContext) -> list[str]:
        errors = []
        if self.config_path and not self.config_path.exists():
            errors.append(f"Configuration file not found: {self.config_path}")
        if self.infra_config_path and not self.infra_config_path.exists():
            errors.append(f"Infrastructure config file not found: {self.infra_config_path}")
        return errors

    def run(self, context: OperationContext) -> ContestConfig:
        contest = load_contest_config(self.config_path, self.contest_name, context.secrets)
        infra = load_infrastructure_config(self.infra_config_path)
        client = APIClientFactory().create_admin_client(infra, context.secrets)
        verify_problemset(client=client, contest=contest, secrets=context.secrets)
        return contest

    def _success_message(self, contest: ContestConfig) -> str:
        return f"Verified {len(contest.problems)} problems"
