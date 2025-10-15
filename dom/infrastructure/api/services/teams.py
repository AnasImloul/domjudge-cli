"""Team management service for DOMjudge API."""

import json
from typing import Any

from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.infrastructure.api.result_types import CreateResult
from dom.logging_config import get_logger
from dom.types.api import models

logger = get_logger(__name__)


class TeamService:
    """
    Service for managing teams in DOMjudge.

    Handles all team-related API operations.
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the team service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def list_for_contest(self, contest_id: str) -> list[dict[str, Any]]:
        """
        List teams for a specific contest.

        Args:
            contest_id: Contest identifier

        Returns:
            List of team dictionaries
        """
        data = self.client.get(
            f"/api/v4/contests/{contest_id}/teams", cache_key=f"contest_{contest_id}_teams"
        )
        logger.debug(f"Fetched {len(data)} teams for contest {contest_id}")
        return data  # type: ignore[return-value]

    def add_to_contest(self, contest_id: str, team_data: models.AddTeam) -> CreateResult:
        """
        Add a team to a contest or get existing one.

        Args:
            contest_id: Contest identifier
            team_data: Team data to add

        Returns:
            CreateResult with team ID and creation status
        """
        # Check if team already exists
        for team in self.list_for_contest(contest_id):
            if team["name"] == team_data.name:
                logger.info(f"Team '{team_data.name}' already exists in contest {contest_id}")
                return CreateResult(id=team["id"], created=False, data=team)

        # Create new team
        data = json.loads(team_data.model_dump_json(exclude_unset=True))
        response = self.client.post(
            f"/api/v4/contests/{contest_id}/teams",
            json=data,
            invalidate_cache=f"contest_{contest_id}_teams",
        )

        if "id" not in response:
            raise APIError(f"No 'id' in team creation response: {response}")

        team_id = response["id"]
        logger.info(f"Created team '{team_data.name}' (ID: {team_id})")

        return CreateResult(id=team_id, created=True, data=response)
