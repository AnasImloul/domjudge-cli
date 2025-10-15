"""Factory for creating DOMjudge API clients with dependency injection.

This module provides centralized creation of API clients and their dependencies.
Use this for consistent configuration and easy testing with mocks.
"""

from dom.constants import DEFAULT_CACHE_TTL, DEFAULT_RATE_BURST, DEFAULT_RATE_LIMIT
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class APIClientFactory:
    """
    Factory for creating API clients with proper dependency injection.

    This centralizes the creation of API clients and ensures consistent
    configuration across the application.

    Design:
        - Stateless factory (no mutable state)
        - Thread-safe by design (immutable configuration)
        - Explicit dependency injection (no globals)
        - Testable (easy to mock/override)

    Usage:
        >>> # Create factory with defaults
        >>> factory = APIClientFactory()
        >>> api = factory.create_admin_client(infra_config, secrets_manager)
        >>>
        >>> # Or with custom configuration
        >>> factory = APIClientFactory(cache_ttl=600, rate_limit=10.0)
        >>> api = factory.create_client("http://localhost:8080", "admin", "password")
        >>>
        >>> # For testing
        >>> test_factory = APIClientFactory(enable_cache=False)
        >>> test_api = test_factory.create_client(...)

    Note:
        This class is intentionally stateless and immutable after construction.
        Configuration is passed at construction time, not stored as mutable state.
        This ensures thread-safety and predictable behavior.
    """

    def __init__(
        self,
        default_cache_ttl: int = DEFAULT_CACHE_TTL,
        default_rate_limit: float = DEFAULT_RATE_LIMIT,
        default_rate_burst: int = DEFAULT_RATE_BURST,
        enable_cache: bool = True,
    ):
        """
        Initialize the API client factory with immutable configuration.

        Args:
            default_cache_ttl: Default cache TTL in seconds
            default_rate_limit: Default requests per second
            default_rate_burst: Default burst capacity
            enable_cache: Whether to enable caching by default
        """
        self.default_cache_ttl = default_cache_ttl
        self.default_rate_limit = default_rate_limit
        self.default_rate_burst = default_rate_burst
        self.enable_cache = enable_cache

        logger.debug(
            f"Initialized API client factory "
            f"(cache={enable_cache}, ttl={default_cache_ttl}s, rate={default_rate_limit}/s)"
        )

    def create_client(
        self,
        base_url: str,
        username: str,
        password: str,
        cache_ttl: int | None = None,
        rate_limit: float | None = None,
        rate_burst: int | None = None,
        enable_cache: bool | None = None,
    ) -> DomJudgeAPI:
        """
        Create a DOMjudge API client with the given credentials.

        Args:
            base_url: Base URL of DOMjudge instance
            username: API username
            password: API password
            cache_ttl: Override default cache TTL
            rate_limit: Override default rate limit
            rate_burst: Override default rate burst
            enable_cache: Override default cache setting

        Returns:
            Configured DOMjudge API client
        """
        api = DomJudgeAPI(
            base_url=base_url,
            username=username,
            password=password,
            cache_ttl=cache_ttl or self.default_cache_ttl,
            rate_limit=rate_limit or self.default_rate_limit,
            rate_burst=rate_burst or self.default_rate_burst,
            enable_cache=enable_cache if enable_cache is not None else self.enable_cache,
        )

        logger.info(f"Created API client for {base_url}")
        return api

    def create_admin_client(
        self, infra: InfraConfig, secrets: SecretsProvider, **kwargs
    ) -> DomJudgeAPI:
        """
        Create an admin API client from infrastructure config.

        Args:
            infra: Infrastructure configuration
            secrets: Secrets manager for retrieving password
            **kwargs: Additional arguments passed to create_client

        Returns:
            Admin API client
        """
        admin_password = secrets.get_required("admin_password")

        return self.create_client(
            base_url=f"http://localhost:{infra.port}",
            username="admin",
            password=admin_password,
            **kwargs,
        )

    def create_test_client(
        self,
        base_url: str = "http://localhost:8080",
        username: str = "admin",
        password: str = "test_password",  # nosec B107
    ) -> DomJudgeAPI:
        """
        Create a test API client with mock-friendly settings.

        Args:
            base_url: Test base URL
            username: Test username
            password: Test password

        Returns:
            Test API client
        """
        return self.create_client(
            base_url=base_url,
            username=username,
            password=password,
            enable_cache=False,  # Disable cache for testing
            rate_limit=1000.0,  # High limit for tests
        )
