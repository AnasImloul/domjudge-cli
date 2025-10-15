"""Organization management service for DOMjudge API."""

import json
from typing import Any

from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.infrastructure.api.result_types import CreateResult
from dom.logging_config import get_logger
from dom.types.api import models

logger = get_logger(__name__)


class OrganizationService:
    """
    Service for managing organizations in DOMjudge.

    Handles all organization-related API operations.
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the organization service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def list_for_contest(self, contest_id: str) -> list[dict[str, Any]]:
        """
        List organizations for a specific contest.

        Args:
            contest_id: Contest identifier

        Returns:
            List of organization dictionaries
        """
        data = self.client.get(f"/api/v4/contests/{contest_id}/organizations")
        logger.debug(f"Fetched {len(data)} organizations for contest {contest_id}")
        return data  # type: ignore[return-value]

    def add_to_contest(self, contest_id: str, organization: models.AddOrganization) -> CreateResult:
        """
        Add an organization to a contest or get existing one.

        Args:
            contest_id: Contest identifier
            organization: Organization data to add

        Returns:
            CreateResult with organization ID and creation status
        """
        # Check if organization already exists
        existing_orgs = self.list_for_contest(contest_id)

        for org in existing_orgs:
            if org.get("name") == organization.name:
                logger.info(
                    f"Organization '{organization.name}' already exists in contest {contest_id}"
                )
                return CreateResult(id=organization.id or org["id"], created=False, data=org)

        # Create new organization
        payload = json.loads(organization.model_dump_json(exclude_unset=True))
        response = self.client.post(f"/api/v4/contests/{contest_id}/organizations", json=payload)

        if "id" not in response:
            raise APIError(f"No 'id' in organization creation response: {response}")

        org_id = response["id"]
        logger.info(f"Created organization '{organization.name}' (ID: {org_id})")

        return CreateResult(id=organization.id or org_id, created=True, data=response)
