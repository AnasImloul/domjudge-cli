"""Submission management service for DOMjudge API."""

import tempfile
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from dom.exceptions import APIError
from dom.infrastructure.api.client import DomJudgeClient
from dom.logging_config import get_logger
from dom.types.api import models
from dom.types.team import Team

logger = get_logger(__name__)


class SubmissionService:
    """
    Service for managing submissions in DOMjudge.

    Handles all submission-related API operations.
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the submission service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def submit(
        self,
        contest_id: str,
        problem_id: str,
        file_name: str,
        language: str,
        source_code: bytes,
        team: Team,
    ) -> models.Submission:
        """
        Submit a solution to a contest problem.

        Args:
            contest_id: Contest identifier
            problem_id: Problem identifier
            file_name: Name of the source file
            language: Programming language
            source_code: Source code as bytes
            team: Team submitting the solution

        Returns:
            Submission model

        Raises:
            APIError: If submission fails
        """
        url = self.client.url(f"/api/v4/contests/{contest_id}/submissions")
        auth = HTTPBasicAuth(team.name, team.password.get_secret_value())

        # Create temp file
        file_suffix = Path(file_name).suffix
        with tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=file_suffix) as tmp_file:
            tmp_file.write(source_code)
            tmp_file_path = Path(tmp_file.name)
        try:
            with tmp_file_path.open("rb") as code_file:
                files = {"code": (file_name, code_file, "text/x-source-code")}
                data = {"problem": problem_id, "language": language, "team": team.id}

                self.client.rate_limiter.acquire()
                response = requests.post(url, data=data, files=files, auth=auth, timeout=30)

                if not response.ok:
                    logger.error(f"Submission failed for '{file_name}': {response.text}")
                    self.client.handle_response_error(response)

                logger.info(f"Submitted '{file_name}' to contest {contest_id} for team {team.name}")
                return models.Submission(**response.json())

        except requests.HTTPError as e:
            logger.error(f"Submission failed for '{file_name}': {e.response.text}")
            raise APIError(f"Submission failed: {e.response.text}") from e
        finally:
            if tmp_file_path.exists():
                tmp_file_path.unlink()

    def get_judgement(self, contest_id: str, submission_id: str) -> models.JudgingWrapper | None:
        """
        Get judgement for a submission.

        Args:
            contest_id: Contest identifier
            submission_id: Submission identifier

        Returns:
            Judgement wrapper or None if not yet judged
        """
        response = self.client.get(
            f"/api/v4/contests/{contest_id}/judgements?submission_id={submission_id}&strict=false"
        )

        judgements = response
        if len(judgements) == 0:
            return None

        logger.debug(f"Fetched judgement for submission {submission_id}")
        return models.JudgingWrapper(**judgements[0])  # type: ignore[index]
