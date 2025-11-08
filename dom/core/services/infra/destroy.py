"""Infrastructure destruction service.

This service handles the safe destruction of infrastructure components,
including stopping Docker containers and optionally removing volumes and secrets.
"""

from dom.infrastructure.docker.containers import DockerClient
from dom.logging_config import get_logger
from dom.shared.filesystem import ensure_dom_directory
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class InfrastructureDestructionService:
    """
    Service for destroying and cleaning up infrastructure components.

    This service encapsulates all operations related to tearing down infrastructure,
    providing a clean boundary between the operations layer and infrastructure layer.
    """

    def __init__(self, docker_client: DockerClient | None = None) -> None:
        """
        Initialize the destruction service.

        Args:
            docker_client: Docker client to use. If None, creates a new instance.
        """
        self._docker = docker_client or DockerClient()
        self._compose_file = ensure_dom_directory() / "docker-compose.yml"

    def destroy(self, secrets: SecretsProvider, remove_volumes: bool = False) -> None:
        """
        Destroy all infrastructure and optionally clean up secrets.

        This stops all Docker services and optionally removes volumes (data).

        Args:
            secrets: Secrets manager to clear if volumes are removed
            remove_volumes: If True, delete volumes (PERMANENT DATA LOSS)

        Raises:
            DockerError: If stopping services fails
        """
        logger.info("Tearing down infrastructure...")

        self._docker.stop_all_services(
            compose_file=self._compose_file,
            remove_volumes=remove_volumes,
        )

        if remove_volumes:
            # Only clear secrets if volumes are deleted
            secrets.clear_all()
            logger.info("All data and secrets cleared")
        else:
            logger.info("Infrastructure stopped. Volumes and secrets preserved for future use")

        logger.info("Clean-up completed")


# Legacy function for backward compatibility - will be removed in future
def destroy_infra_and_platform(secrets: SecretsProvider, remove_volumes: bool = False) -> None:
    """
    Destroy all infrastructure and clean up secrets.

    .. deprecated:: 2.0
        Use InfrastructureDestructionService.destroy() instead.

    Args:
        secrets: Secrets manager to clear
        remove_volumes: If True, delete volumes (PERMANENT DATA LOSS)
    """
    service = InfrastructureDestructionService()
    service.destroy(secrets, remove_volumes)
