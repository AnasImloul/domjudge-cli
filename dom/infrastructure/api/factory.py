"""Factory for creating DOMjudge API clients with dependency injection.

This module provides centralized creation of API clients and their dependencies.
Use this for consistent configuration and easy testing with mocks.
"""

from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class APIClientFactory:
    """
    Factory for creating API clients with proper dependency injection.

    Centralizes client construction so services never depend on
    infrastructure construction. Stateless and thread-safe.

    Usage:
        >>> factory = APIClientFactory()
        >>> api = factory.create_admin_client(infra_config, secrets_manager)
    """

    def create_client(
        self,
        base_url: str,
        username: str,
        password: str,
    ) -> DomJudgeAPI:
        """Create a DOMjudge API client with the given credentials."""
        api = DomJudgeAPI(base_url=base_url, username=username, password=password)
        logger.info(f"Created API client for {base_url}")
        return api

    def create_admin_client(self, infra: InfraConfig, secrets: SecretsProvider) -> DomJudgeAPI:
        """Create an admin API client from infrastructure config."""
        admin_password = secrets.get_required("admin_password")
        return self.create_client(
            base_url=f"http://localhost:{infra.port}",
            username="admin",
            password=admin_password,
        )
