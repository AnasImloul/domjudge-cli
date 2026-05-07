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
        except APIError as e:
            # DOMjudge returns HTTP 400 when a contest with the same
            # shortname already exists. Re-fetch and return the existing
            # row instead of failing — keeps creation idempotent for
            # initial-setup flows. Any other APIError propagates.
            if e.status_code == 400 and contest_data.shortname:
                existing = self._find_by_shortname(contest_data.shortname)
                if existing is not None:
                    logger.info(
                        "Contest already exists",
                        extra={"contest_shortname": contest_data.shortname},
                    )
                    contest_data.id = existing["id"]
                    return CreateResult(id=existing["id"], created=False, data=contest_data)
                logger.error(
                    f"Contest creation rejected (400) but no contest "
                    f"with shortname '{contest_data.shortname}' was found",
                )
                raise APIError(
                    f"Contest creation rejected: {e}",
                    status_code=e.status_code,
                    response_body=e.response_body,
                ) from e
            raise

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

    def _find_by_shortname(self, shortname: str) -> dict[str, Any] | None:
        """Return the contest dict matching the given shortname, if any."""
        for contest in self.list_all():
            if contest.get("shortname") == shortname:
                return contest
        return None
