"""Infrastructure service.

Encapsulates Docker, compose generation, credential bootstrap, lifecycle, and
status checks so that operations can stay declarative and only describe the
sequence of steps.
"""

import subprocess  # nosec B404
from pathlib import Path

import yaml

from dom.constants import ContainerNames
from dom.exceptions import DockerError
from dom.infrastructure.docker.containers import DockerClient
from dom.infrastructure.docker.template import generate_docker_compose
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig, InfrastructureStatus, ServiceStatus
from dom.types.secrets import SecretsProvider
from dom.utils.cli import ensure_dom_directory, get_container_prefix
from dom.utils.validation import (
    validate_infrastructure_prerequisites,
    warn_if_privileged_port,
)

logger = get_logger(__name__)

_BOOTSTRAP_JUDGE_PASSWORD = "TEMP"  # nosec B105


class InfraService:
    """Declarative service for infrastructure orchestration."""

    def __init__(self, secrets: SecretsProvider):
        self.secrets = secrets
        self._docker = DockerClient()
        self._compose_file = ensure_dom_directory() / "docker-compose.yml"

    # ------------------------------------------------------------------ Validation

    def validate_prerequisites(self, port: int) -> None:
        validate_infrastructure_prerequisites(port)

    def warn_privileged_port(self, port: int) -> None:
        warn_if_privileged_port(port)

    # ------------------------------------------------------------------ Compose

    def generate_compose_bootstrap(self, config: InfraConfig) -> None:
        """Generate docker-compose with a placeholder judgedaemon password."""
        generate_docker_compose(
            config, secrets=self.secrets, judge_password=_BOOTSTRAP_JUDGE_PASSWORD
        )

    def regenerate_compose(self, config: InfraConfig) -> None:
        """Regenerate docker-compose using the judgedaemon password from secrets."""
        judge_password = self.secrets.get_required("judge_password")
        generate_docker_compose(config, secrets=self.secrets, judge_password=judge_password)

    # ------------------------------------------------------------------ Lifecycle

    def start_service(self, service: str) -> None:
        self._docker.start_services([service], self._compose_file)

    def wait_domserver_healthy(self) -> None:
        prefix = get_container_prefix()
        self._docker.wait_for_container_healthy(ContainerNames.DOMSERVER.with_prefix(prefix))

    def fetch_and_store_judge_password(self) -> str:
        """Fetch the judgedaemon password from DOMserver and persist it in secrets."""
        password = self._docker.fetch_judgedaemon_password()
        self.secrets.set("judge_password", password)
        return password

    def start_judgehosts(self, count: int) -> None:
        services = [f"judgehost-{i + 1}" for i in range(count)]
        self._docker.start_services(services, self._compose_file)

    def configure_admin_password(self, config: InfraConfig) -> None:
        admin_password = (
            config.password.get_secret_value()
            if config.password
            else self.secrets.get("admin_password") or self._docker.fetch_admin_init_password()
        )
        self._docker.update_admin_password(
            new_password=admin_password,
            db_user="domjudge",
            db_password=self.secrets.get_required("db_password"),
        )
        self.secrets.set("admin_password", admin_password)

    # ------------------------------------------------------------------ Destruction

    def destroy(self, remove_volumes: bool = False) -> None:
        """Stop services and optionally delete volumes (PERMANENT DATA LOSS)."""
        logger.info("Tearing down infrastructure...")
        self._docker.stop_all_services(
            compose_file=self._compose_file, remove_volumes=remove_volumes
        )
        if remove_volumes:
            self.secrets.clear_all()
            logger.info("All data and secrets cleared")
        else:
            logger.info("Infrastructure stopped. Volumes and secrets preserved for future use")
        logger.info("Clean-up completed")

    # ------------------------------------------------------------------ Status

    def check_status(self) -> InfrastructureStatus:
        """Check the health of Docker, expected services, and their containers."""
        status = InfrastructureStatus()

        try:
            DockerClient()
            status.docker_available = True
        except DockerError as e:
            status.docker_available = False
            status.docker_error = str(e)
            logger.error(f"Docker is not available: {e}")
            return status

        expected_services = self._expected_services()
        if not expected_services:
            logger.warning("No services found in docker-compose.yml or file doesn't exist")
            return status

        for service_name, container_name in expected_services.items():
            service_status, details = self._container_status(container_name)
            status.services[service_name] = service_status
            status.service_details[service_name] = details

        logger.info(
            "Infrastructure status check complete",
            extra={
                "healthy": status.is_healthy(),
                "services_count": len(status.services),
                "healthy_services": sum(
                    1 for s in status.services.values() if s == ServiceStatus.HEALTHY
                ),
            },
        )
        return status

    def _expected_services(self) -> dict[str, str]:
        """Parse docker-compose.yml to extract {service_name: container_name}."""
        if not self._compose_file.exists():
            logger.warning(f"Docker compose file not found at {self._compose_file}")
            return {}

        try:
            with Path(self._compose_file).open() as f:
                compose_data = yaml.safe_load(f)
            services = {
                name: cfg.get("container_name", name)
                for name, cfg in compose_data.get("services", {}).items()
            }
            logger.debug(
                f"Found {len(services)} services in docker-compose.yml: {list(services.keys())}"
            )
            return services
        except Exception as e:
            logger.error(f"Failed to parse docker-compose.yml: {e}", exc_info=True)
            return {}

    def _container_status(self, container_name: str) -> tuple[ServiceStatus, dict]:
        """Inspect a container and classify its state + health."""
        try:
            state_cmd = [
                *self._docker._cmd,
                "inspect",
                "--format={{.State.Status}}",
                container_name,
            ]
            state_result = subprocess.run(  # nosec B603
                state_cmd, capture_output=True, text=True, check=False
            )
            if state_result.returncode != 0:
                return ServiceStatus.MISSING, {
                    "container": container_name,
                    "error": "Container not found",
                }

            container_state = state_result.stdout.strip()
            if container_state != "running":
                return ServiceStatus.STOPPED, {
                    "container": container_name,
                    "state": container_state,
                }

            health_cmd = [
                *self._docker._cmd,
                "inspect",
                "--format={{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}",
                container_name,
            ]
            health_result = subprocess.run(  # nosec B603
                health_cmd, capture_output=True, text=True, check=False
            )
            health = (
                health_result.stdout.strip() if health_result.returncode == 0 else "no_healthcheck"
            )

            base_details = {
                "container": container_name,
                "state": container_state,
                "health": health,
            }
            if health == "starting":
                return ServiceStatus.STARTING, base_details
            if health == "unhealthy":
                return ServiceStatus.UNHEALTHY, base_details
            return ServiceStatus.HEALTHY, base_details

        except Exception as e:
            logger.error(
                f"Failed to check container status: {e}",
                exc_info=True,
                extra={"container": container_name},
            )
            return ServiceStatus.MISSING, {"container": container_name, "error": str(e)}
