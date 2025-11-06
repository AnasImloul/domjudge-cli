"""Team group management service for DOMjudge API."""

from typing import Any

from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.infrastructure.api.result_types import CreateResult
from dom.logging_config import get_logger

logger = get_logger(__name__)


class GroupAPIService:
    """
    Infrastructure API service for managing team groups/categories in DOMjudge.

    This is a thin wrapper around HTTP API calls.

    Team groups allow organizing teams and controlling which teams
    appear on each contest's scoreboard.
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the group API service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def list_for_contest(self, contest_id: str) -> list[dict[str, Any]]:
        """
        List team groups for a specific contest.

        Args:
            contest_id: Contest identifier

        Returns:
            List of group dictionaries
        """
        data = self.client.get(
            f"/api/v4/contests/{contest_id}/groups", cache_key=f"contest_{contest_id}_groups"
        )
        logger.debug(f"Fetched {len(data)} groups for contest {contest_id}")
        return data  # type: ignore[return-value]

    def create_for_contest(
        self, contest_id: str, name: str, group_id: str | None = None
    ) -> CreateResult:
        """
        Create a team group for a contest or get existing one.

        Args:
            contest_id: Contest identifier
            name: Group name (e.g., "JNJD Teams")
            group_id: Optional group ID (will be auto-generated if not provided)

        Returns:
            CreateResult with group ID and creation status
        """
        # Check if group already exists
        existing_groups = self.list_for_contest(contest_id)

        for group in existing_groups:
            if group.get("name") == name:
                logger.info(f"Group '{name}' already exists in contest {contest_id}")
                return CreateResult(id=group["id"], created=False, data=group)

        # Create new group
        payload = {"name": name}
        if group_id:
            payload["id"] = group_id

        response = self.client.post(
            f"/api/v4/contests/{contest_id}/groups",
            json=payload,
            invalidate_cache=f"contest_{contest_id}_groups",
        )

        if "id" not in response:
            raise APIError(f"No 'id' in group creation response: {response}")

        created_group_id = response["id"]
        logger.info(f"Created group '{name}' (ID: {created_group_id}) in contest {contest_id}")

        return CreateResult(id=created_group_id, created=True, data=response)
