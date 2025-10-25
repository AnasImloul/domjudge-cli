"""Infrastructure destruction service."""

from dom.infrastructure.docker.containers import DockerClient
from dom.logging_config import get_logger
from dom.types.secrets import SecretsProvider
from dom.utils.cli import ensure_dom_directory

logger = get_logger(__name__)


def destroy_infra_and_platform(secrets: SecretsProvider, remove_volumes: bool = False) -> None:
    """
        Destroy all infrastructure and clean up secrets.

    This stops all Docker services and optionally removes volumes (data).

    Args:
        secrets: Secrets manager to clear
        remove_volumes: If True, delete volumes (PERMANENT DATA LOSS)

    Raises:
        DockerError: If stopping services fails
    """
    logger.info("Tearing down infrastructure...")

    docker = DockerClient()
    compose_file = ensure_dom_directory() / "docker-compose.yml"

    docker.stop_all_services(compose_file=compose_file, remove_volumes=remove_volumes)

    if remove_volumes:
        # Only clear secrets if volumes are deleted
        secrets.clear_all()
        logger.info("All data and secrets cleared")
    else:
        logger.info("Infrastructure stopped. Volumes and secrets preserved for future use")

    logger.info("Clean-up completed")
