"""Temporary contest creation for verification."""

import secrets
import string
from datetime import datetime

from dom.core.services.base import ServiceContext
from dom.core.services.problem.apply import ProblemService
from dom.core.services.protocols import DomJudgeAPIProtocol
from dom.core.services.team.apply import TeamService
from dom.exceptions import ContestError, ProblemError, TeamError
from dom.types.api.models import Contest
from dom.types.contest import ContestConfig
from dom.types.secrets import SecretsProvider
from dom.types.team import Team

_TEMP_NAME_SUFFIX_LENGTH = 8
_TEMP_CONTEST_START = datetime.fromisoformat("2020-01-01T00:00:00+01:00")
_TEMP_CONTEST_DURATION = "10:00:00.000"


def create_temp_contest(
    client: DomJudgeAPIProtocol, contest: ContestConfig, secrets_mgr: SecretsProvider
) -> tuple[Contest, Team]:
    """Create a throwaway contest plus a single team, used to verify problems.

    Raises ``ContestError`` / ``ProblemError`` / ``TeamError`` on failure.
    """
    temp_name = f"Temp-{contest.shortname}-{_random_suffix()}"

    api_contest = Contest(
        name=f"Temp {contest.name or contest.shortname}",
        shortname=temp_name,
        formal_name=contest.formal_name or contest.name,
        start_time=_TEMP_CONTEST_START,
        duration=_TEMP_CONTEST_DURATION,
        allow_submit=True,
    )

    result = client.contests.create(api_contest)
    if not result.created:
        raise ContestError(f"Failed to create temporary contest '{temp_name}'")
    if result.id is None:
        raise ContestError(f"Temporary contest '{temp_name}' was created without an ID")

    temp_team = Team(
        name=temp_name,
        username=temp_name,
        password=secrets_mgr.generate_deterministic_password(seed=temp_name, length=12),
    )
    context = ServiceContext(client=client, contest_id=result.id, contest_shortname=temp_name)

    problem_service = ProblemService(client)
    team_service = TeamService(client)

    problem_results = problem_service.create_many(contest.problems, context, stop_on_error=False)
    problem_summary = problem_service.get_summary(problem_results)
    if problem_summary["failed"] > 0:
        raise ProblemError(
            f"{problem_summary['failed']} problem(s) failed to add to temporary contest"
        )

    team_results = team_service.create_many([temp_team], context, stop_on_error=False)
    team_summary = team_service.get_summary(team_results)
    if team_summary["failed"] > 0:
        raise TeamError(f"{team_summary['failed']} team(s) failed to add to temporary contest")
    if temp_team.id is None:
        raise TeamError(f"Temporary team '{temp_name}' was created without an ID")

    return api_contest, temp_team


def _random_suffix() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(_TEMP_NAME_SUFFIX_LENGTH))
