"""Problem management service for DOMjudge API."""

import tempfile
from pathlib import Path
from typing import Any

from dom.constants import LONG_CACHE_TTL
from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.logging_config import get_logger
from dom.types.problem import ProblemPackage

logger = get_logger(__name__)


class ProblemService:
    """
    Service for managing problems in DOMjudge.

    Handles all problem-related API operations.
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the problem service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def list_for_contest(self, contest_id: str) -> list[dict[str, Any]]:
        """
        List problems for a specific contest.

        Args:
            contest_id: Contest identifier

        Returns:
            List of problem dictionaries
        """
        data = self.client.get(
            f"/api/v4/contests/{contest_id}/problems", cache_key=f"contest_{contest_id}_problems"
        )
        logger.debug(f"Fetched {len(data)} problems for contest {contest_id}")
        return data  # type: ignore[return-value]

    def list_all(self) -> dict[str, Any]:
        """
        List all problems across all contests.

        Returns:
            Dictionary mapping external IDs to problem data
        """
        cache_key = "all_problems"
        if self.client.cache:
            cached = self.client.cache.get(cache_key)
            if cached:
                logger.debug("Using cached all_problems")
                return cached  # type: ignore[no-any-return]

        all_problems = {}

        # Get all contests (assuming ContestService is accessible)
        contests_data = self.client.get("/api/v4/contests", cache_key="contests_list")

        logger.info(f"Fetching problems from {len(contests_data)} contests")

        for contest in contests_data:
            contest_id = contest["id"]  # type: ignore[index]
            problems = self.list_for_contest(contest_id)
            for problem in problems:
                externalid = problem.get("externalid")
                if externalid and externalid not in all_problems:
                    all_problems[externalid] = problem

        if self.client.cache:
            self.client.cache.set(cache_key, all_problems, ttl=LONG_CACHE_TTL)

        logger.info(f"Found {len(all_problems)} unique problems")
        return all_problems

    def create_or_get(self, problem_package: ProblemPackage) -> str:
        """
        Create a problem or get existing one by external ID.

        Args:
            problem_package: Problem package to upload

        Returns:
            Problem ID
        """
        all_problems = self.list_all()
        externalid = problem_package.ini.externalid

        if externalid in all_problems:
            problem_id = all_problems[externalid]["id"]
            logger.info(f"Problem '{externalid}' already exists (ID: {problem_id})")
            return problem_id  # type: ignore[no-any-return]

        # Create new problem
        temp_zip_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                temp_zip_path = Path(temp_zip.name)
                problem_package.write_to_zip(temp_zip_path)

            with temp_zip_path.open("rb") as f:
                files = {"zip": (f.name, f, "application/zip")}
                response = self.client.post(
                    "/api/v4/problems", files=files, invalidate_cache="all_problems"
                )

                if "problem_id" not in response:
                    raise APIError(f"No 'problem_id' in response: {response}")

                problem_id = response["problem_id"]
                logger.info(f"Created problem (ID: {problem_id})")
                return problem_id  # type: ignore[no-any-return]
        finally:
            if temp_zip_path and temp_zip_path.exists():
                temp_zip_path.unlink()

    def add_to_contest(self, contest_id: str, problem_package: ProblemPackage) -> str:
        """
        Add a problem to a contest.

        Args:
            contest_id: Contest identifier
            problem_package: Problem package

        Returns:
            Problem ID
        """
        problem_id = self.create_or_get(problem_package)

        # Check if already linked
        existing_problems = self.list_for_contest(contest_id)
        if problem_id in [p["id"] for p in existing_problems]:
            logger.info(f"Problem {problem_id} already linked to contest {contest_id}")
            return problem_id

        # Link to contest
        self.client.put(
            f"/api/v4/contests/{contest_id}/problems/{problem_id}",
            json={"label": problem_package.yaml.name, "color": problem_package.ini.color},
            invalidate_cache=f"contest_{contest_id}_problems",
        )

        logger.info(f"Linked problem {problem_id} to contest {contest_id}")
        return problem_id
