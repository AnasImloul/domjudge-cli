"""Infrastructure destruction service."""

from dom.infrastructure.docker.containers import DockerClient
from dom.logging_config import get_logger
from dom.types.secrets import SecretsProvider
from dom.utils.cli import ensure_dom_directory

logger = get_logger(__name__)


def destroy_infra_and_platform(secrets: SecretsProvider) -> None:
    """
    Destroy all infrastructure and clean up secrets.

    This stops all Docker services and clears all stored secrets.

    Args:
        secrets: Secrets manager to clear

    Raises:
        DockerError: If stopping services fails
    """
    logger.warning("🔥 DESTROY: Tearing down infrastructure...")

    docker = DockerClient()
    compose_file = ensure_dom_directory() / "docker-compose.yml"

    docker.stop_all_services(compose_file=compose_file)
    secrets.clear_all()

    logger.warning("🔥 DESTROY: Clean-up done.")
