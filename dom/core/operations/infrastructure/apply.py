"""Apply infrastructure configuration operation."""

from typing import Any

from dom.constants import ContainerNames
from dom.core.operations.base import (
    ExecutableStep,
    OperationContext,
    OperationResult,
    SteppedOperation,
)
from dom.infrastructure.docker.containers import DockerClient
from dom.infrastructure.docker.template import generate_docker_compose
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig
from dom.utils.cli import ensure_dom_directory, get_container_prefix
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

    def __init__(self, config: InfraConfig, judge_password: str = "TEMP"):  # nosec B107
        super().__init__("generate_compose", "Generate docker-compose.yml")
        self.config = config
        self.judge_password = judge_password

    def execute(self, context: OperationContext) -> None:
        """Generate docker-compose file."""
        generate_docker_compose(
            self.config, secrets=context.secrets, judge_password=self.judge_password
        )


class StartDatabaseStep(ExecutableStep):
    """Step to start MariaDB container."""

    def __init__(self):
        super().__init__("start_database", "Start MariaDB container")

    def execute(self, _context: OperationContext) -> None:
        """Start the MariaDB database container."""
        docker = DockerClient()
        compose_file = ensure_dom_directory() / "docker-compose.yml"
        docker.start_services(["mariadb"], compose_file)


class StartMySQLClientStep(ExecutableStep):
    """Step to start MySQL client container."""

    def __init__(self):
        super().__init__("start_mysql_client", "Start MySQL client container")

    def execute(self, _context: OperationContext) -> None:
        """Start the MySQL client container."""
        docker = DockerClient()
        compose_file = ensure_dom_directory() / "docker-compose.yml"
        docker.start_services(["mysql-client"], compose_file)


class StartDOMServerStep(ExecutableStep):
    """Step to start DOMserver container."""

    def __init__(self):
        super().__init__("start_domserver", "Start DOMserver container")

    def execute(self, _context: OperationContext) -> None:
        """Start the DOMserver container."""
        docker = DockerClient()
        compose_file = ensure_dom_directory() / "docker-compose.yml"
        docker.start_services(["domserver"], compose_file)


class WaitForHealthyStep(ExecutableStep):
    """Step to wait for DOMserver to become healthy."""

    def __init__(self):
        super().__init__("wait_healthy", "Wait for DOMserver to be healthy")

    def execute(self, _context: OperationContext) -> None:
        """Wait for DOMserver container to be healthy."""
        docker = DockerClient()
        container_prefix = get_container_prefix()
        docker.wait_for_container_healthy(ContainerNames.DOMSERVER.with_prefix(container_prefix))


class FetchJudgePasswordStep(ExecutableStep):
    """Step to fetch judgedaemon password from DOMserver."""

    def __init__(self):
        super().__init__("fetch_password", "Fetch judgedaemon password")

    def execute(self, context: OperationContext) -> str:
        """Fetch the judgedaemon password from the running DOMserver and store it in secrets."""
        docker = DockerClient()
        judge_password = docker.fetch_judgedaemon_password()

        # Store in context secrets so RegenerateComposeStep can access it
        context.secrets.set("judge_password", judge_password)

        return judge_password


class RegenerateComposeStep(ExecutableStep):
    """Step to regenerate docker-compose with real judgedaemon password."""

    def __init__(self, config: InfraConfig):
        super().__init__("regenerate_compose", "Regenerate docker-compose with real password")
        self.config = config

    def execute(self, context: OperationContext) -> None:
        """Regenerate docker-compose file with real password from secrets."""
        # Get judge password from secrets (stored by FetchJudgePasswordStep)
        judge_password = context.secrets.get_required("judge_password")

        # Regenerate compose with real password
        generate_docker_compose(self.config, secrets=context.secrets, judge_password=judge_password)


class StartJudgehostsStep(ExecutableStep):
    """Step to start judgehost containers."""

    def __init__(self, judge_count: int):
        super().__init__("start_judgehosts", f"Start {judge_count} judgehost(s)")
        self.judge_count = judge_count

    def execute(self, _context: OperationContext) -> None:
        """Start the judgehost containers."""
        docker = DockerClient()
        compose_file = ensure_dom_directory() / "docker-compose.yml"
        judgehost_services = [f"judgehost-{i + 1}" for i in range(self.judge_count)]
        docker.start_services(judgehost_services, compose_file)


class ConfigureAdminPasswordStep(ExecutableStep):
    """Step to configure admin password."""

    def __init__(self, config: InfraConfig):
        super().__init__("configure_admin", "Configure admin password")
        self.config = config

    def execute(self, context: OperationContext) -> None:
        """Configure the admin password in the database."""
        docker = DockerClient()
        admin_password = (
            self.config.password.get_secret_value()
            if self.config.password
            else context.secrets.get("admin_password") or docker.fetch_admin_init_password()
        )

        docker.update_admin_password(
            new_password=admin_password,
            db_user="domjudge",
            db_password=context.secrets.get_required("db_password"),
        )
        context.secrets.set("admin_password", admin_password)


# ============================================================================
# Operation
# ============================================================================


class ApplyInfrastructureOperation(SteppedOperation[None]):
    """Apply infrastructure configuration (setup Docker containers, etc.)."""

    def __init__(self, config: InfraConfig):
        """
        Initialize infrastructure application operation.

        Args:
            config: Infrastructure configuration
        """
        self.config = config

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
            GenerateComposeStep(self.config, judge_password="TEMP"),  # nosec B106
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
        """Build final result."""
        return OperationResult.success(
            None,
            f"Infrastructure ready at http://localhost:{self.config.port} • {self.config.judges} judgehost(s) running",
        )
