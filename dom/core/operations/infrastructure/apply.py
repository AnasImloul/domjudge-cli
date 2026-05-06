"""Apply infrastructure configuration operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.service import InfraService
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class ValidatePrerequisitesStep(ExecutableStep):
    def __init__(self, port: int):
        super().__init__("validate", "Validate prerequisites")
        self.port = port

    def execute(self, context: OperationContext) -> None:
        service = InfraService(context.secrets)
        service.validate_prerequisites(self.port)
        service.warn_privileged_port(self.port)


class GenerateComposeStep(ExecutableStep):
    def __init__(self, config: InfraConfig):
        super().__init__("generate_compose", "Generate docker-compose.yml")
        self.config = config

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).generate_compose_bootstrap(self.config)


class StartDatabaseStep(ExecutableStep):
    def __init__(self):
        super().__init__("start_database", "Start MariaDB container")

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).start_service("mariadb")


class StartMySQLClientStep(ExecutableStep):
    def __init__(self):
        super().__init__("start_mysql_client", "Start MySQL client container")

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).start_service("mysql-client")


class StartDOMServerStep(ExecutableStep):
    def __init__(self):
        super().__init__("start_domserver", "Start DOMserver container")

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).start_service("domserver")


class WaitForHealthyStep(ExecutableStep):
    def __init__(self):
        super().__init__("wait_healthy", "Wait for DOMserver to be healthy")

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).wait_domserver_healthy()


class FetchJudgePasswordStep(ExecutableStep):
    def __init__(self):
        super().__init__("fetch_password", "Fetch judgedaemon password")

    def execute(self, context: OperationContext) -> str:
        return InfraService(context.secrets).fetch_and_store_judge_password()


class RegenerateComposeStep(ExecutableStep):
    def __init__(self, config: InfraConfig):
        super().__init__("regenerate_compose", "Regenerate docker-compose with real password")
        self.config = config

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).regenerate_compose(self.config)


class StartJudgehostsStep(ExecutableStep):
    def __init__(self, judge_count: int):
        super().__init__("start_judgehosts", f"Start {judge_count} judgehost(s)")
        self.judge_count = judge_count

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).start_judgehosts(self.judge_count)


class ConfigureAdminPasswordStep(ExecutableStep):
    def __init__(self, config: InfraConfig):
        super().__init__("configure_admin", "Configure admin password")
        self.config = config

    def execute(self, context: OperationContext) -> None:
        InfraService(context.secrets).configure_admin_password(self.config)


# ============================================================================
# Operation
# ============================================================================


class ApplyInfrastructureOperation(SteppedOperation[None]):
    """Apply infrastructure configuration (setup Docker containers, etc.)."""

    def __init__(self, config: InfraConfig):
        self.config = config

    def describe(self) -> str:
        return "Deploy infrastructure and platform components"

    def validate(self, context: OperationContext) -> list[str]:
        errors = []
        try:
            InfraService(context.secrets).validate_prerequisites(self.config.port)
        except Exception as e:
            errors.append(str(e))
        return errors

    def define_steps(self) -> list[ExecutableStep]:
        return [
            ValidatePrerequisitesStep(self.config.port),
            GenerateComposeStep(self.config),
            StartDatabaseStep(),
            StartMySQLClientStep(),
            StartDOMServerStep(),
            WaitForHealthyStep(),
            FetchJudgePasswordStep(),
            RegenerateComposeStep(self.config),
            StartJudgehostsStep(self.config.judges),
            ConfigureAdminPasswordStep(self.config),
        ]

    def _build_result(
        self,
        _step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        return OperationResult.success(
            None,
            f"Infrastructure ready at http://0.0.0.0:{self.config.port} • {self.config.judges} judgehost(s) running",
        )
