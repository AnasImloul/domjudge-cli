"""Contest management service for DOMjudge API."""

from io import BytesIO
from typing import Any

from dom.constants import SHORT_CACHE_TTL
from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.infrastructure.api.result_types import CreateResult
from dom.logging_config import get_logger
from dom.types.api import models

logger = get_logger(__name__)


class ContestService:
    """
    Service for managing contests in DOMjudge.

    Handles all contest-related API operations including:
    - Listing contests
    - Creating contests
    - Updating contests
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the contest service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def list_all(self) -> list[dict[str, Any]]:
        """
        List all contests.

        Returns:
            List of contest dictionaries

        Raises:
            APIError: If request fails
        """
        data = self.client.get(
            "/api/v4/contests",
            cache_key="contests_list",
            cache_ttl=SHORT_CACHE_TTL,  # Shorter TTL for frequently changing data
        )

        logger.debug(f"Fetched {len(data)} contests")
        return data  # type: ignore[return-value]

    def create(self, contest_data: models.Contest) -> CreateResult:
        """
        Create a contest or get existing one by shortname.

        Args:
            contest_data: Contest data to create

        Returns:
            CreateResult with contest ID and creation status

        Raises:
            APIError: If contest creation fails
        """
        contest_json = contest_data.model_dump_json()
        file_like = BytesIO(contest_json.encode("utf-8"))
        files = {"json": ("contest.json", file_like, "application/json")}

        try:
            response = self.client.post(
                "/api/v4/contests", files=files, invalidate_cache="contests_list"
            )

            logger.info(
                "Created new contest",
                extra={
                    "contest_shortname": contest_data.shortname,
                    "contest_name": contest_data.name,
                },
            )

            contest_id = response
            contest_data.id = contest_id  # type: ignore[assignment]

            return CreateResult(id=contest_id, created=True, data=contest_data)  # type: ignore[arg-type]

        except Exception as e:
            # Check if contest already exists
            if "shortname" in str(e).lower():
                existing_contests = self.list_all()
                for contest in existing_contests:
                    if contest.get("shortname") == contest_data.shortname:
                        logger.info(
                            "Contest already exists",
                            extra={"contest_shortname": contest_data.shortname},
                        )
                        contest_data.id = contest["id"]
                        return CreateResult(id=contest["id"], created=False, data=contest_data)

                logger.error(
                    f"Contest with shortname '{contest_data.shortname}' not found after error"
                )
                raise APIError(
                    f"Contest with shortname '{contest_data.shortname}' exists but could not fetch it."
                ) from None

            logger.error(f"Failed to create contest: {e}")
            raise
