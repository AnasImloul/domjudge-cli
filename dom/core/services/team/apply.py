from typing import List
import sys


from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.types.team import Team
from dom.types.api.models import AddTeam, AddUser
from dom.utils.unicode import clean_team_name


def apply_teams_to_contest(client: DomJudgeAPI, contest_id: str, teams: List[Team]):
    for idx, team in enumerate(teams, start=1):
        try:
            highest_id = max([int(other_team["id"]) for other_team in client.list_contest_teams(contest_id)])
            team_id = client.add_team_to_contest(
                contest_id=contest_id,
                team_data=AddTeam(
                    id=str(highest_id + 1),
                    name=clean_team_name(team.name, allow_spaces=False),
                    display_name=team.name,
                    group_ids=["3"],
                )
            )

            user_id = client.add_user(
                user_data=AddUser(
                    username=clean_team_name(team.name, allow_spaces=False),
                    name=clean_team_name(team.name, allow_spaces=False),
                    password=team.password.get_secret_value(),
                    team_id=team_id,
                    roles=[
                        "team"
                    ]
                )
            )

        except Exception as e:
            print(f"[ERROR] Contest {contest_id}: Failed to prepare team from row {idx}. Unexpected error: {str(e)}",
                  file=sys.stderr)
