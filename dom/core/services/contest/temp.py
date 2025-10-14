"""Temporary contest creation for verification."""

import secrets
import string
from datetime import datetime

from dom.core.services.problem.apply import apply_problems_to_contest
from dom.core.services.team.apply import apply_teams_to_contest
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.infrastructure.secrets.manager import SecretsManager
from dom.types.api.models import Contest
from dom.types.contest import ContestConfig
from dom.types.team import Team


def create_temp_contest(
    client: DomJudgeAPI, contest: ContestConfig, secrets_mgr: SecretsManager
) -> tuple[Contest, Team]:
    """
    Create a temporary contest for verification purposes.

    Args:
        client: DOMjudge API client
        contest: Contest configuration
        secrets_mgr: Secrets manager for password generation

    Returns:
        Tuple of (Contest, Team) for the temporary contest
    """
    # Generate random suffix for uniqueness
    alphabet = string.ascii_letters + string.digits
    random_suffix = "".join(secrets.choice(alphabet) for _ in range(8))
    temp_name = f"Temp-{contest.shortname}-{random_suffix}"

    api_contest = Contest(
        name=f"Temp {contest.name or contest.shortname}",
        shortname=temp_name,
        formal_name=contest.formal_name or contest.name,
        start_time=datetime.fromisoformat("2020-01-01T00:00:00+01:00"),
        duration="10:00:00.000",
        allow_submit=True,
    )

    result = client.contests.create(api_contest)
    contest_id = result.id
    created = result.created

    assert created, "Failed to create temporary contest"
    assert contest_id is not None, "Contest ID is None"

    temp_team = Team(
        name=temp_name,
        username=temp_name,
        password=secrets_mgr.generate_deterministic_password(seed=temp_name, length=12),
    )

    apply_problems_to_contest(client, contest_id, contest.problems)
    apply_teams_to_contest(client, contest_id, [temp_team])

    assert temp_team.id is not None, "Team ID is None"

    return api_contest, temp_team
