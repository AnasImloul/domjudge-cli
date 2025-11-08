"""Team management service for DOMjudge API."""

import json
from typing import Any

from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.infrastructure.api.result_types import CreateResult
from dom.logging_config import get_logger
from dom.types.api import models

logger = get_logger(__name__)


class TeamAPIService:
    """
    Infrastructure API service for managing teams in DOMjudge.

    This is a thin wrapper around HTTP API calls. For business logic,
    see dom.core.services.team.apply.TeamService.

    Handles all team-related API operations.
    """

    def __init__(self, client: DomJudgeClient) -> None:
        """
        Initialize the team API service.

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
        # Check if team already exists in this contest
        # Uses deterministic composite name matching for accuracy
        try:
            existing_teams = self.list_for_contest(contest_id)
            logger.debug(f"Checking for duplicate team among {len(existing_teams)} existing teams")

            # Build set of existing composite names from API
            existing_composite_names = {
                team.get("name") for team in existing_teams if team.get("name")
            }

            # Check if team already exists by composite name
            # team_data.name is the composite name built by TeamApplicationService
            # Format: "team####|name|affiliation|country"
            if team_data.name in existing_composite_names:
                matching_team = next(
                    (t for t in existing_teams if t.get("name") == team_data.name), None
                )

                if matching_team:
                    display_name = getattr(team_data, "display_name", "Unknown")
                    logger.info(
                        f"✓ Team '{display_name}' already exists in contest {contest_id} - skipping "
                        f"(matched composite name: '{team_data.name}')"
                    )
                    return CreateResult(id=matching_team["id"], created=False, data=matching_team)

            logger.debug(f"Team with composite name '{team_data.name}' not found, will create")
        except Exception as e:
            logger.warning(
                f"Failed to check for duplicate team: {e}. "
                f"Proceeding with creation (may fail if duplicate)",
                exc_info=True,
            )

        # Create new team in this contest
        # Note: Each contest gets its own team instance, but with consistent global identifiers
        data = json.loads(team_data.model_dump_json(exclude_unset=True))
        response = self.client.post(
            f"/api/v4/contests/{contest_id}/teams",
            json=data,
            invalidate_cache=f"contest_{contest_id}_teams",
        )

        if "id" not in response:
            raise APIError(f"No 'id' in team creation response: {response}")

        team_id = response["id"]
        logger.info(f"Created team '{team_data.name}' (ID: {team_id}) in contest {contest_id}")

        return CreateResult(id=team_id, created=True, data=response)
