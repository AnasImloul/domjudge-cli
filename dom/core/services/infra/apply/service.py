"""Infrastructure and platform deployment service.

This module handles the orchestration of Docker containers and platform configuration
for DOMjudge infrastructure deployment.
"""

from dom.infrastructure.docker.containers import DockerClient
from dom.infrastructure.docker.template import generate_docker_compose
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider
from dom.utils.cli import ensure_dom_directory

logger = get_logger(__name__)


def apply_infra_and_platform(infra_config: InfraConfig, secrets: SecretsProvider) -> None:
    """
    Deploy and configure DOMjudge infrastructure.

    This orchestrates the deployment of all infrastructure components including:
    - Docker Compose generation
    - MariaDB database
    - DOMjudge server
    - Judgehost containers
    - Admin password configuration

    Args:
        infra_config: Infrastructure configuration
        secrets: Secrets manager for storing and retrieving secrets

    Raises:
        DockerError: If any Docker operation fails
        SecretsError: If secrets management fails
    """
    # Initialize Docker client
    docker = DockerClient()
    compose_file = ensure_dom_directory() / "docker-compose.yml"

    logger.info("Step 1: Generating initial docker-compose configuration...")
    # Temporary password before real one is fetched from domserver
    generate_docker_compose(infra_config, secrets=secrets, judge_password="TEMP")  # nosec B106

    logger.info("Step 2: Starting core services (MariaDB + Domserver + MySQL Client)...")
    docker.start_services(["mariadb", "mysql-client", "domserver"], compose_file)

    logger.info("Waiting for Domserver to be healthy...")
    docker.wait_for_container_healthy("dom-cli-domserver")

    logger.info("Step 3: Fetching judgedaemon password...")
    judge_password = docker.fetch_judgedaemon_password()

    logger.info("Step 4: Regenerating docker-compose with real judgedaemon password...")
    generate_docker_compose(infra_config, secrets=secrets, judge_password=judge_password)

    logger.info(f"Step 5: Starting {infra_config.judges} judgehosts...")
    judgehost_services = [f"judgehost-{i + 1}" for i in range(infra_config.judges)]
    docker.start_services(judgehost_services, compose_file)

    logger.info("Step 6: Updating admin password...")
    admin_password = (
        infra_config.password.get_secret_value()
        if infra_config.password
        else None or secrets.get("admin_password") or docker.fetch_admin_init_password()
    )

    docker.update_admin_password(
        new_password=admin_password,
        db_user="domjudge",
        db_password=secrets.get_required("db_password"),
    )
    secrets.set("admin_password", admin_password)

    logger.info(
        "✅ Infrastructure and platform are ready!",
        extra={"port": infra_config.port, "judgehosts": infra_config.judges},
    )
    logger.info(f"   - DOMjudge server: http://localhost:{infra_config.port}")
    logger.info(f"   - Judgehosts: {infra_config.judges} active")
    logger.info("   - Admin password: stored securely")
