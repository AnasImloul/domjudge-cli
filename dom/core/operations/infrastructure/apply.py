"""Apply infrastructure configuration operation."""

from typing import Any

from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.core.services.infra.deployment import InfrastructureDeploymentService
from dom.logging_config import get_logger
from dom.types.config.processed import InfraConfig
from dom.utils.validation import (
    validate_infrastructure_prerequisites,
    warn_if_privileged_port,
)

logger = get_logger(__name__)


# ============================================================================
# Steps
# ============================================================================


class ValidatePrerequisitesStep(ExecutableStep):
    """Step to validate infrastructure prerequisites."""

    def __init__(self, port: int):
        super().__init__("validate", "Validate prerequisites")
        self.port = port

    def execute(self, _context: OperationContext) -> None:
        """Validate prerequisites and warn about privileged ports."""
        validate_infrastructure_prerequisites(self.port)
        warn_if_privileged_port(self.port)


class GenerateComposeStep(ExecutableStep):
    """Step to generate docker-compose.yml file."""

    def __init__(
        self,
        config: InfraConfig,
        deployment_service: InfrastructureDeploymentService,
        judge_password: str = "TEMP",  # nosec B107
    ):
        super().__init__("generate_compose", "Generate docker-compose.yml")
        self.config = config
        self.deployment_service = deployment_service
        self.judge_password = judge_password

    def execute(self, context: OperationContext) -> None:
        """Generate docker-compose file."""
        self.deployment_service.generate_compose_file(
            self.config, secrets=context.secrets, judge_password=self.judge_password
        )


class StartDatabaseStep(ExecutableStep):
    """Step to start MariaDB container."""

    def __init__(self, deployment_service: InfrastructureDeploymentService):
        super().__init__("start_database", "Start MariaDB container")
        self.deployment_service = deployment_service

    def execute(self, _context: OperationContext) -> None:
        """Start the MariaDB database container."""
        self.deployment_service.start_database()


class StartMySQLClientStep(ExecutableStep):
    """Step to start MySQL client container."""

    def __init__(self, deployment_service: InfrastructureDeploymentService):
        super().__init__("start_mysql_client", "Start MySQL client container")
        self.deployment_service = deployment_service

    def execute(self, _context: OperationContext) -> None:
        """Start the MySQL client container."""
        self.deployment_service.start_mysql_client()


class StartDOMServerStep(ExecutableStep):
    """Step to start DOMserver container."""

    def __init__(self, deployment_service: InfrastructureDeploymentService):
        super().__init__("start_domserver", "Start DOMserver container")
        self.deployment_service = deployment_service

    def execute(self, _context: OperationContext) -> None:
        """Start the DOMserver container."""
        self.deployment_service.start_domserver()


class WaitForHealthyStep(ExecutableStep):
    """Step to wait for DOMserver to become healthy."""

    def __init__(self, deployment_service: InfrastructureDeploymentService):
        super().__init__("wait_healthy", "Wait for DOMserver to be healthy")
        self.deployment_service = deployment_service

    def execute(self, _context: OperationContext) -> None:
        """Wait for DOMserver container to be healthy."""
        self.deployment_service.wait_for_domserver_healthy()


class FetchJudgePasswordStep(ExecutableStep):
    """Step to fetch judgedaemon password from DOMserver."""

    def __init__(self, deployment_service: InfrastructureDeploymentService):
        super().__init__("fetch_password", "Fetch judgedaemon password")
        self.deployment_service = deployment_service

    def execute(self, context: OperationContext) -> str:
        """Fetch the judgedaemon password from the running DOMserver and store it in secrets."""
        judge_password = self.deployment_service.fetch_judgedaemon_password()

        # Store in context secrets so RegenerateComposeStep can access it
        context.secrets.set("judge_password", judge_password)

        return judge_password


class RegenerateComposeStep(ExecutableStep):
    """Step to regenerate docker-compose with real judgedaemon password."""

    def __init__(self, config: InfraConfig, deployment_service: InfrastructureDeploymentService):
        super().__init__("regenerate_compose", "Regenerate docker-compose with real password")
        self.config = config
        self.deployment_service = deployment_service

    def execute(self, context: OperationContext) -> None:
        """Regenerate docker-compose file with real password from secrets."""
        # Get judge password from secrets (stored by FetchJudgePasswordStep)
        judge_password = context.secrets.get_required("judge_password")

        # Regenerate compose with real password
        self.deployment_service.generate_compose_file(
            self.config, secrets=context.secrets, judge_password=judge_password
        )


class StartJudgehostsStep(ExecutableStep):
    """Step to start judgehost containers."""

    def __init__(self, judge_count: int, deployment_service: InfrastructureDeploymentService):
        super().__init__("start_judgehosts", f"Start {judge_count} judgehost(s)")
        self.judge_count = judge_count
        self.deployment_service = deployment_service

    def execute(self, _context: OperationContext) -> None:
        """Start the judgehost containers."""
        self.deployment_service.start_judgehosts(self.judge_count)


class ConfigureAdminPasswordStep(ExecutableStep):
    """Step to configure admin password."""

    def __init__(self, config: InfraConfig, deployment_service: InfrastructureDeploymentService):
        super().__init__("configure_admin", "Configure admin password")
        self.config = config
        self.deployment_service = deployment_service

    def execute(self, context: OperationContext) -> None:
        """Configure the admin password in the database."""
        admin_password = (
            self.config.password.get_secret_value()
            if self.config.password
            else context.secrets.get("admin_password")
            or self.deployment_service.fetch_admin_init_password()
        )

        self.deployment_service.configure_admin_password(
            admin_password=admin_password,
            db_password=context.secrets.get_required("db_password"),
        )
        context.secrets.set("admin_password", admin_password)


# ============================================================================
# Operation
# ============================================================================


class ApplyInfrastructureOperation(SteppedOperation[None]):
    """Apply infrastructure configuration (setup Docker containers, etc.)."""

    def __init__(
        self,
        config: InfraConfig,
        deployment_service: InfrastructureDeploymentService | None = None,
    ):
        """
        Initialize infrastructure application operation.

        Args:
            config: Infrastructure configuration
            deployment_service: Service for infrastructure deployment. If None, creates a new instance.
        """
        self.config = config
        self._deployment_service = deployment_service or InfrastructureDeploymentService()

    def describe(self) -> str:
        """Describe what this operation does."""
        return "Deploy infrastructure and platform components"

    def validate(self, _context: OperationContext) -> list[str]:
        """Validate prerequisites before deployment."""
        errors = []
        try:
            validate_infrastructure_prerequisites(self.config.port)
        except Exception as e:
            errors.append(str(e))
        return errors

    def define_steps(self) -> list[ExecutableStep]:
        """Define the steps for deploying infrastructure."""
        return [
            ValidatePrerequisitesStep(self.config.port),
            GenerateComposeStep(self.config, self._deployment_service, judge_password="TEMP"),  # nosec B106
            StartDatabaseStep(self._deployment_service),
            StartMySQLClientStep(self._deployment_service),
            StartDOMServerStep(self._deployment_service),
            WaitForHealthyStep(self._deployment_service),
            FetchJudgePasswordStep(self._deployment_service),
            RegenerateComposeStep(self.config, self._deployment_service),
            StartJudgehostsStep(self.config.judges, self._deployment_service),
            ConfigureAdminPasswordStep(self.config, self._deployment_service),
        ]

    def _build_result(
        self,
        _step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[None]:
        """Build final result."""
        return OperationResult.success(
            None,
            f"Infrastructure ready at http://0.0.0.0:{self.config.port} • {self.config.judges} judgehost(s) running",
        )
