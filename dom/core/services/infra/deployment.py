"""Infrastructure deployment service.

This service orchestrates the deployment of infrastructure components,
including Docker container management, compose file generation, and password configuration.
It acts as a facade over the infrastructure layer, providing business-level operations.
"""

from pathlib import Path

from dom.constants import ContainerNames
from dom.infrastructure.docker.containers import DockerClient
from dom.infrastructure.docker.template import generate_docker_compose
from dom.logging_config import get_logger
from dom.shared.filesystem import ensure_dom_directory, get_container_prefix
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class InfrastructureDeploymentService:
    """
    Service for deploying and managing infrastructure components.

    This service encapsulates all Docker-related operations for infrastructure deployment,
    providing a clean boundary between the operations layer and infrastructure layer.
    """

    def __init__(self, docker_client: DockerClient | None = None):
        """
        Initialize the deployment service.

        Args:
            docker_client: Docker client to use. If None, creates a new instance.
        """
        self._docker = docker_client or DockerClient()
        self._compose_file = ensure_dom_directory() / "docker-compose.yml"

    @property
    def compose_file(self) -> Path:
        """Get the path to the docker-compose file."""
        return self._compose_file

    def generate_compose_file(
        self,
        config: InfraConfig,
        secrets: SecretsProvider,
        judge_password: str,
    ) -> None:
        """
        Generate docker-compose.yml file.

        Args:
            config: Infrastructure configuration
            secrets: Secrets provider for sensitive data
            judge_password: Password for judgedaemon authentication
        """
        logger.info("Generating docker-compose.yml")
        generate_docker_compose(config, secrets=secrets, judge_password=judge_password)

    def start_database(self) -> None:
        """Start the MariaDB database container."""
        logger.info("Starting MariaDB container")
        self._docker.start_services(["mariadb"], self._compose_file)

    def start_mysql_client(self) -> None:
        """Start the MySQL client container."""
        logger.info("Starting MySQL client container")
        self._docker.start_services(["mysql-client"], self._compose_file)

    def start_domserver(self) -> None:
        """Start the DOMserver container."""
        logger.info("Starting DOMserver container")
        self._docker.start_services(["domserver"], self._compose_file)

    def wait_for_domserver_healthy(self) -> None:
        """Wait for DOMserver container to become healthy."""
        logger.info("Waiting for DOMserver to be healthy")
        container_prefix = get_container_prefix()
        container_name = ContainerNames.DOMSERVER.with_prefix(container_prefix)
        self._docker.wait_for_container_healthy(container_name)

    def fetch_judgedaemon_password(self) -> str:
        """
        Fetch judgedaemon password from the running DOMserver.

        Returns:
            The judgedaemon password

        Raises:
            DockerError: If password retrieval fails
        """
        logger.info("Fetching judgedaemon password from DOMserver")
        return self._docker.fetch_judgedaemon_password()

    def start_judgehosts(self, judge_count: int) -> None:
        """
        Start the specified number of judgehost containers.

        Args:
            judge_count: Number of judgehost containers to start
        """
        logger.info(f"Starting {judge_count} judgehost(s)")
        judgehost_services = [f"judgehost-{i + 1}" for i in range(judge_count)]
        self._docker.start_services(judgehost_services, self._compose_file)

    def configure_admin_password(
        self,
        admin_password: str,
        db_password: str,
        db_user: str = "domjudge",
    ) -> None:
        """
        Configure the admin password in the database.

        Args:
            admin_password: New admin password to set
            db_password: Database password for authentication
            db_user: Database user (default: domjudge)
        """
        logger.info("Configuring admin password")
        self._docker.update_admin_password(
            new_password=admin_password,
            db_user=db_user,
            db_password=db_password,
        )

    def fetch_admin_init_password(self) -> str:
        """
        Fetch the initial admin password from DOMserver.

        Returns:
            The initial admin password

        Raises:
            DockerError: If password retrieval fails
        """
        logger.info("Fetching initial admin password")
        return self._docker.fetch_admin_init_password()

    def stop_all_services(self, remove_volumes: bool = False) -> None:
        """
        Stop all infrastructure services.

        Args:
            remove_volumes: If True, also remove volumes (PERMANENT DATA LOSS)
        """
        if remove_volumes:
            logger.warning("Stopping all services and removing volumes (PERMANENT DATA LOSS)")
        else:
            logger.info("Stopping all services (volumes will be preserved)")

        self._docker.stop_all_services(
            compose_file=self._compose_file,
            remove_volumes=remove_volumes,
        )
