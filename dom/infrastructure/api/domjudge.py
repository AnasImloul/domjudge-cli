"""DOMjudge API client - Clean facade over focused service classes.

This is the main API client that all code should use. It provides a clean interface
through service composition rather than being a monolithic God class.

Architecture:
- DomJudgeClient: Base HTTP client (auth, caching, rate limiting)
- Service classes: Focused on specific resources (contests, problems, teams, etc.)
- DomJudgeAPI: Facade that composes services

Single Way to Use:
    >>> from dom.infrastructure.api.factory import APIClientFactory
    >>>
    >>> # Create factory
    >>> factory = APIClientFactory()
    >>>
    >>> # Create API client
    >>> api = factory.create_admin_client(infra, secrets)
    >>>
    >>> # Use services (ONLY way)
    >>> contests = api.contests.list_all()
    >>> api.problems.add_to_contest(contest_id, problem_pkg)
    >>> api.teams.add_to_contest(contest_id, team_data)
"""

from dom.constants import DEFAULT_CACHE_TTL, DEFAULT_RATE_BURST, DEFAULT_RATE_LIMIT
from dom.infrastructure.api.client import DomJudgeClient
from dom.infrastructure.api.services import (
    ContestService,
    OrganizationService,
    ProblemService,
    SubmissionService,
    TeamService,
    UserService,
)
from dom.logging_config import get_logger

logger = get_logger(__name__)


class DomJudgeAPI:
    """
    DOMjudge API client using service composition.

    This facade provides access to focused service classes organized by resource type.
    There is ONLY ONE WAY to use this API - through the service properties.

    Services:
        api.contests      - Contest operations
        api.problems      - Problem operations
        api.teams         - Team operations
        api.users         - User operations
        api.organizations - Organization operations
        api.submissions   - Submission operations

    Example:
        >>> factory = APIClientFactory()
        >>> api = factory.create_client("http://localhost:8080", "admin", "password")
        >>>
        >>> # Use services (ONLY way)
        >>> contests = api.contests.list_all()
        >>> result = api.contests.create(contest_data)
        >>> api.problems.add_to_contest(contest_id, problem_pkg)
        >>> api.teams.add_to_contest(contest_id, team_data)
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        enable_cache: bool = True,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        rate_burst: int = DEFAULT_RATE_BURST,
    ):
        """
        Initialize the DOMjudge API client.

        Args:
            base_url: Base URL of the DOMjudge instance
            username: API username
            password: API password
            enable_cache: Enable response caching
            cache_ttl: Cache time-to-live in seconds
            rate_limit: Requests per second limit
            rate_burst: Maximum burst size
        """
        # Create base HTTP client
        self.client = DomJudgeClient(
            base_url=base_url,
            username=username,
            password=password,
            enable_cache=enable_cache,
            cache_ttl=cache_ttl,
            rate_limit=rate_limit,
            rate_burst=rate_burst,
        )

        # Compose focused services
        self.contests = ContestService(self.client)
        self.problems = ProblemService(self.client)
        self.teams = TeamService(self.client)
        self.users = UserService(self.client)
        self.organizations = OrganizationService(self.client)
        self.submissions = SubmissionService(self.client)

        logger.info(f"Initialized DOMjudge API client for {base_url}")
