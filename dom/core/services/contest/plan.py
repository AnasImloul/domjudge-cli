"""Contest planning service for dry-run previews."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from dom.exceptions import APIError
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.infrastructure.api.factory import APIClientFactory
from dom.logging_config import get_logger
from dom.types.config import DomConfig
from dom.types.config.processed import ContestConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class ChangeAction(str, Enum):
    """Types of changes that can be made to resources."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    LINK = "LINK"
    SKIP = "SKIP"


@dataclass
class ResourceChange:
    """
    Represents a planned change to a resource.

    Attributes:
        resource_type: Type of resource (contest, problem, team)
        action: Action to be performed (CREATE, UPDATE, LINK, SKIP)
        identifier: Resource identifier (name, shortname, etc.)
        details: Human-readable description of the change
        count: Optional count for bulk operations
    """

    resource_type: str
    action: ChangeAction
    identifier: str
    details: str
    count: int | None = None


@dataclass
class ContestPlan:
    """
    Complete plan of changes for a contest configuration.

    Attributes:
        changes: List of all planned changes
        contest_count: Number of contests to be configured
        total_problems: Total number of problems across all contests
        total_teams: Total number of teams across all contests
    """

    changes: list[ResourceChange]
    contest_count: int
    total_problems: int
    total_teams: int


class ContestPlanner:
    """
    Service for planning contest changes without applying them.

    This service analyzes what changes would be made if contests were applied,
    without actually making any modifications to the DOMjudge platform.

    Usage:
        >>> planner = ContestPlanner(api_client, config)
        >>> plan = planner.plan_changes()
        >>> for change in plan.changes:
        ...     print(f"{change.action}: {change.resource_type} - {change.details}")
    """

    def __init__(self, client: DomJudgeAPI, config: DomConfig):
        """
        Initialize the contest planner.

        Args:
            client: DOMjudge API client
            config: Complete DOMjudge configuration
        """
        self.client = client
        self.config = config

    def plan_changes(self) -> ContestPlan:
        """
        Analyze what changes would be made if contests were applied.

        Returns:
            Complete plan of all changes

        Raises:
            APIError: If unable to connect to DOMjudge API
        """
        changes: list[ResourceChange] = []
        total_problems = 0
        total_teams = 0

        # Fetch existing contests once
        existing_contests = self._fetch_existing_contests()
        existing_contest_map = {c.get("shortname"): c for c in existing_contests}

        # Plan changes for each contest
        for contest in self.config.contests:
            contest_changes = self._plan_contest_changes(contest, existing_contest_map)  # type: ignore[arg-type]
            changes.extend(contest_changes)

            total_problems += len(contest.problems)
            total_teams += len(contest.teams)

        return ContestPlan(
            changes=changes,
            contest_count=len(self.config.contests),
            total_problems=total_problems,
            total_teams=total_teams,
        )

    def _fetch_existing_contests(self) -> list[dict[str, Any]]:
        """
        Fetch existing contests from DOMjudge.

        Returns:
            List of existing contest dictionaries
        """
        try:
            return self.client.contests.list_all()
        except APIError as e:
            logger.warning(f"Could not fetch existing contests: {e}")
            return []

    def _plan_contest_changes(
        self, contest: ContestConfig, existing_contest_map: dict[str, dict[str, Any]]
    ) -> list[ResourceChange]:
        """
        Plan changes for a single contest.

        Args:
            contest: Contest configuration
            existing_contest_map: Map of shortname to existing contest data

        Returns:
            List of changes for this contest
        """
        changes: list[ResourceChange] = []

        # Check if contest exists
        existing_contest = existing_contest_map.get(contest.shortname)  # type: ignore[arg-type]

        if existing_contest:
            changes.append(
                ResourceChange(
                    resource_type="contest",
                    action=ChangeAction.UPDATE,
                    identifier=contest.shortname,  # type: ignore[arg-type]
                    details=f"Existing contest '{contest.name}' will be updated",
                )
            )
            contest_id = existing_contest["id"]
        else:
            changes.append(
                ResourceChange(
                    resource_type="contest",
                    action=ChangeAction.CREATE,
                    identifier=contest.shortname,  # type: ignore[arg-type]
                    details=f"New contest '{contest.name}' will be created",
                )
            )
            contest_id = None

        # Plan problem changes
        problem_changes = self._plan_problem_changes(contest, contest_id)
        changes.extend(problem_changes)

        # Plan team changes
        team_changes = self._plan_team_changes(contest, contest_id)
        changes.extend(team_changes)

        return changes

    def _plan_problem_changes(
        self, contest: ContestConfig, contest_id: str | None
    ) -> list[ResourceChange]:
        """
        Plan problem changes for a contest.

        Args:
            contest: Contest configuration
            contest_id: Existing contest ID (None if new contest)

        Returns:
            List of problem changes
        """
        problems_count = len(contest.problems)

        if contest_id is None:
            # New contest - all problems will be added
            return [
                ResourceChange(
                    resource_type="problems",
                    action=ChangeAction.CREATE,
                    identifier=contest.shortname,  # type: ignore[arg-type]
                    details=f"{problems_count} problem(s) will be added",
                    count=problems_count,
                )
            ]

        # Existing contest - check current problems
        try:
            existing_problems = self.client.problems.list_for_contest(contest_id)
            existing_count = len(existing_problems)
            new_count = max(0, problems_count - existing_count)

            if new_count > 0:
                return [
                    ResourceChange(
                        resource_type="problems",
                        action=ChangeAction.CREATE,
                        identifier=contest.shortname,  # type: ignore[arg-type]
                        details=f"{new_count} new problem(s), {existing_count} existing",
                        count=problems_count,
                    )
                ]
            else:
                return [
                    ResourceChange(
                        resource_type="problems",
                        action=ChangeAction.LINK,
                        identifier=contest.shortname,  # type: ignore[arg-type]
                        details=f"{problems_count} problem(s) already linked",
                        count=problems_count,
                    )
                ]
        except APIError as e:
            logger.debug(f"Could not fetch existing problems: {e}")
            return [
                ResourceChange(
                    resource_type="problems",
                    action=ChangeAction.CREATE,
                    identifier=contest.shortname,  # type: ignore[arg-type]
                    details=f"{problems_count} problem(s) configured",
                    count=problems_count,
                )
            ]

    def _plan_team_changes(
        self, contest: ContestConfig, contest_id: str | None
    ) -> list[ResourceChange]:
        """
        Plan team changes for a contest.

        Args:
            contest: Contest configuration
            contest_id: Existing contest ID (None if new contest)

        Returns:
            List of team changes
        """
        teams_count = len(contest.teams)

        if contest_id is None:
            # New contest - all teams will be added
            return [
                ResourceChange(
                    resource_type="teams",
                    action=ChangeAction.CREATE,
                    identifier=contest.shortname,  # type: ignore[arg-type]
                    details=f"{teams_count} team(s) will be added",
                    count=teams_count,
                )
            ]

        # Existing contest - check current teams
        try:
            existing_teams = self.client.teams.list_for_contest(contest_id)
            existing_count = len(existing_teams)
            new_count = max(0, teams_count - existing_count)

            if new_count > 0:
                return [
                    ResourceChange(
                        resource_type="teams",
                        action=ChangeAction.CREATE,
                        identifier=contest.shortname,  # type: ignore[arg-type]
                        details=f"{new_count} new team(s), {existing_count} existing",
                        count=teams_count,
                    )
                ]
            else:
                return [
                    ResourceChange(
                        resource_type="teams",
                        action=ChangeAction.LINK,
                        identifier=contest.shortname,  # type: ignore[arg-type]
                        details=f"{teams_count} team(s) already linked",
                        count=teams_count,
                    )
                ]
        except APIError as e:
            logger.debug(f"Could not fetch existing teams: {e}")
            return [
                ResourceChange(
                    resource_type="teams",
                    action=ChangeAction.CREATE,
                    identifier=contest.shortname,  # type: ignore[arg-type]
                    details=f"{teams_count} team(s) configured",
                    count=teams_count,
                )
            ]


def plan_contest_changes(config: DomConfig, secrets: SecretsProvider) -> ContestPlan:
    """
    Plan what changes would be made to contests.

    This is a service-layer function that operations should call.

    Args:
        config: Complete DOMjudge configuration
        secrets: Secrets manager for API credentials

    Returns:
        Contest plan with all planned changes
    """
    factory = APIClientFactory()
    client = factory.create_admin_client(config.infra, secrets)
    planner = ContestPlanner(client, config)
    return planner.plan_changes()
