"""Infrastructure and platform deployment service.

This module handles the orchestration of Docker containers and platform configuration
for DOMjudge infrastructure deployment.
"""

from dom.constants import ContainerNames
from dom.core.services.infra.rollback import (
    DeploymentStep,
    DeploymentTransaction,
    with_rollback,
)
from dom.infrastructure.docker.containers import DockerClient
from dom.infrastructure.docker.template import generate_docker_compose
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider
from dom.utils.cli import ensure_dom_directory, get_container_prefix

logger = get_logger(__name__)


def apply_infra_and_platform(infra_config: InfraConfig, secrets: SecretsProvider) -> None:
    """
    Deploy and configure DOMjudge infrastructure with automatic rollback on failure.

    This orchestrates the deployment of all infrastructure components including:
    - Docker Compose generation
    - MariaDB database
    - DOMjudge server
    - Judgehost containers
    - Admin password configuration

    If any step fails, automatically rolls back all completed steps.

    Args:
        infra_config: Infrastructure configuration
        secrets: Secrets manager for storing and retrieving secrets

    Raises:
        DockerError: If any Docker operation fails
        SecretsError: If secrets management fails
        InfrastructureError: If deployment fails (after rollback)
    """
    # Initialize deployment transaction for rollback support
    transaction = DeploymentTransaction()
    transaction.compose_file = ensure_dom_directory() / "docker-compose.yml"
    transaction.docker_client = DockerClient()

    @with_rollback(transaction)
    def _deploy() -> None:
        """Inner deployment function with rollback support."""
        docker = transaction.docker_client
        compose_file = transaction.compose_file

        # Type assertions - these are guaranteed to be set by the transaction
        assert docker is not None, "Docker client must be initialized"
        assert compose_file is not None, "Compose file must be initialized"
        container_prefix = get_container_prefix()

        logger.info("Step 1: Generating initial docker-compose configuration...")
        # Temporary password before real one is fetched from domserver
        generate_docker_compose(infra_config, secrets=secrets, judge_password="TEMP")  # nosec B106
        transaction.record_step(DeploymentStep.GENERATE_COMPOSE)

        logger.info("Step 2: Starting core services (MariaDB + Domserver + MySQL Client)...")
        docker.start_services(["mariadb"], compose_file)
        transaction.record_step(DeploymentStep.START_DATABASE)

        docker.start_services(["mysql-client"], compose_file)
        transaction.record_step(DeploymentStep.START_MYSQL_CLIENT)

        docker.start_services(["domserver"], compose_file)
        transaction.record_step(DeploymentStep.START_DOMSERVER)

        logger.info("Waiting for Domserver to be healthy...")
        docker.wait_for_container_healthy(ContainerNames.DOMSERVER.with_prefix(container_prefix))

        logger.info("Step 3: Fetching judgedaemon password...")
        judge_password = docker.fetch_judgedaemon_password()

        logger.info("Step 4: Regenerating docker-compose with real judgedaemon password...")
        generate_docker_compose(infra_config, secrets=secrets, judge_password=judge_password)
        transaction.record_step(DeploymentStep.REGENERATE_COMPOSE)

        logger.info(f"Step 5: Starting {infra_config.judges} judgehosts...")
        judgehost_services = [f"judgehost-{i + 1}" for i in range(infra_config.judges)]
        docker.start_services(judgehost_services, compose_file)
        transaction.record_step(DeploymentStep.START_JUDGEHOSTS)

        logger.info("Step 6: Updating admin password...")
        admin_password = (
            infra_config.password.get_secret_value()
            if infra_config.password
            else secrets.get("admin_password") or docker.fetch_admin_init_password()
        )

        docker.update_admin_password(
            new_password=admin_password,
            db_user="domjudge",
            db_password=secrets.get_required("db_password"),
        )
        secrets.set("admin_password", admin_password)
        transaction.record_step(DeploymentStep.UPDATE_ADMIN_PASSWORD)

    # Execute deployment with rollback support
    _deploy()

    logger.info(
        "[OK] Infrastructure and platform are ready!",
        extra={"port": infra_config.port, "judgehosts": infra_config.judges},
    )
    logger.info(f"   - DOMjudge server: http://localhost:{infra_config.port}")
    logger.info(f"   - Judgehosts: {infra_config.judges} active")
    logger.info("   - Admin password: stored securely")
