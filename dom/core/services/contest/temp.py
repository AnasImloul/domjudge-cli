"""Temporary contest creation for verification."""

import secrets
import string
from datetime import datetime

from dom.core.services.base import ServiceContext
from dom.core.services.problem.apply import ProblemService
from dom.core.services.team.apply import TeamService
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.types.api.models import Contest
from dom.types.contest import ContestConfig
from dom.types.secrets import SecretsProvider
from dom.types.team import Team


def create_temp_contest(
    client: DomJudgeAPI, contest: ContestConfig, secrets_mgr: SecretsProvider
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

    # Create service context
    context = ServiceContext(client=client, contest_id=contest_id)

    # Use declarative services
    problem_service = ProblemService(client)
    team_service = TeamService(client)

    # Apply problems
    problem_results = problem_service.create_many(contest.problems, context, stop_on_error=False)
    problem_summary = problem_service.get_summary(problem_results)
    assert problem_summary["failed"] == 0, f"{problem_summary['failed']} problems failed to add"

    # Apply team
    team_results = team_service.create_many([temp_team], context, stop_on_error=False)
    team_summary = team_service.get_summary(team_results)
    assert team_summary["failed"] == 0, f"{team_summary['failed']} teams failed to add"

    assert temp_team.id is not None, "Team ID is None"

    return api_contest, temp_team
