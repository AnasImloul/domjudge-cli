from typing import Tuple
from dom.types.contest import ContestConfig
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.infrastructure.secrets.manager import generate_random_string, generate_secure_password
from dom.types.api.models import Contest
from dom.core.services.problem.apply import apply_problems_to_contest
from dom.core.services.team.apply import apply_teams_to_contest
from dom.types.team import Team


def create_temp_contest(client: DomJudgeAPI,  contest: ContestConfig) -> Tuple[Contest, Team]:
    temp_name = f"Temp-{contest.shortname}-{generate_random_string(length=8)}"

    api_contest = Contest(
        name=f"Temp {contest.name or contest.shortname}",
        shortname=temp_name,
        formal_name=contest.formal_name or contest.name,
        start_time="2020-05-11T11:00:00+01:00",
        duration="10:00:00.000",
        allow_submit=True,
    )

    contest_id, created = client.create_contest(api_contest)

    assert created
    assert api_contest.id is not None

    temp_team = Team(
        name=temp_name,
        username=temp_name,
        password=generate_secure_password(length=12, seed=temp_name)
    )

    apply_problems_to_contest(client, contest_id, contest.problems)
    apply_teams_to_contest(client, contest_id, [temp_team])

    assert temp_team.id is not None

    return api_contest, temp_team