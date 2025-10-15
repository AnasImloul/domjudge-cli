"""Dependency injection container for clean dependency management.

This module provides a declarative way to define and resolve dependencies
without relying on global state or implicit dependencies.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from dom.infrastructure.api.factory import APIClientFactory
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig

logger = get_logger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """
    Dependency injection container using declarative service definitions.

    This container provides:
    1. Explicit dependency declaration
    2. Lazy initialization
    3. Singleton services (shared instances)
    4. Factory services (new instances each time)
    5. Type-safe service resolution

    Example:
        >>> container = ServiceContainer()
        >>> container.register_singleton("secrets", lambda: SecretsManager(Path(".dom")))
        >>> container.register_factory("api_factory", lambda: APIClientFactory())
        >>> secrets = container.get("secrets")
    """

    def __init__(self):
        """Initialize empty container."""
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._singletons: dict[str, Callable[[], Any]] = {}

    def register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a singleton service (shared instance).

        The factory function will be called once, and the same instance
        will be returned for all subsequent calls.

        Args:
            name: Service name
            factory: Function that creates the service
        """
        self._singletons[name] = factory
        logger.debug(f"Registered singleton service: {name}")

    def register_factory(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a factory service (new instance each time).

        The factory function will be called each time the service is requested.

        Args:
            name: Service name
            factory: Function that creates the service
        """
        self._factories[name] = factory
        logger.debug(f"Registered factory service: {name}")

    def register_instance(self, name: str, instance: T) -> None:
        """
        Register an existing instance.

        Args:
            name: Service name
            instance: Service instance
        """
        self._services[name] = instance
        logger.debug(f"Registered service instance: {name}")

    def get(self, name: str) -> Any:
        """
        Get a service by name.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Check if already instantiated
        if name in self._services:
            return self._services[name]

        # Check if singleton (instantiate once)
        if name in self._singletons:
            instance = self._singletons[name]()
            self._services[name] = instance
            logger.debug(f"Instantiated singleton service: {name}")
            return instance

        # Check if factory (instantiate each time)
        if name in self._factories:
            instance = self._factories[name]()
            logger.debug(f"Created factory service instance: {name}")
            return instance

        raise KeyError(f"Service '{name}' not registered")

    def has(self, name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            name: Service name

        Returns:
            True if service is registered
        """
        return name in self._services or name in self._singletons or name in self._factories

    def clear(self) -> None:
        """Clear all services (useful for testing)."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Cleared all services")


class ServiceProvider:
    """
    Provider pattern for accessing commonly used services.

    This provides a higher-level interface over the container
    with type-safe methods for common services.
    """

    def __init__(self, container: ServiceContainer):
        """
        Initialize provider with container.

        Args:
            container: Service container
        """
        self.container = container

    def secrets_manager(self) -> SecretsManager:
        """Get secrets manager service."""
        return cast(SecretsManager, self.container.get("secrets"))

    def api_client_factory(self) -> APIClientFactory:
        """Get API client factory service."""
        return cast(APIClientFactory, self.container.get("api_factory"))

    def create_api_client(self, infra: InfraConfig):
        """
        Create an API client for the given infrastructure.

        Args:
            infra: Infrastructure configuration

        Returns:
            Configured API client
        """
        factory = self.api_client_factory()
        secrets = self.secrets_manager()
        return factory.create_admin_client(infra, secrets)


def create_default_container(dom_directory: Path | None = None) -> ServiceContainer:
    """
    Create a container with default service registrations.

    Args:
        dom_directory: Optional .dom directory path

    Returns:
        Configured service container
    """
    container = ServiceContainer()

    # Determine .dom directory
    if dom_directory is None:
        dom_directory = Path.cwd() / ".dom"
        dom_directory.mkdir(exist_ok=True)

    # Register core services
    container.register_singleton(
        "secrets",
        lambda: SecretsManager(dom_directory),
    )

    container.register_singleton(
        "api_factory",
        lambda: APIClientFactory(),
    )

    logger.info("Created default service container")
    return container


# Global container instance (can be replaced for testing)
_default_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    """
    Get the global service container.

    Returns:
        Global service container
    """
    global _default_container  # noqa: PLW0603
    if _default_container is None:
        _default_container = create_default_container()
    return _default_container


def set_container(container: ServiceContainer) -> None:
    """
    Set the global service container (useful for testing).

    Args:
        container: New container to use
    """
    global _default_container  # noqa: PLW0603
    _default_container = container
    logger.debug("Replaced global service container")


def reset_container() -> None:
    """Reset the global container (useful for testing)."""
    global _default_container  # noqa: PLW0603
    _default_container = None
    logger.debug("Reset global service container")
