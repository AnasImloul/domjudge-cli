from typing import List, Optional
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.types.team import Team
from dom.types.api.models import AddTeam, AddUser, AddOrganization
from dom.utils.unicode import clean_team_name


def apply_teams_to_contest(client: DomJudgeAPI, contest_id: str, teams: List[Team]) -> List[Optional[Team]]:
    results: List[Optional[Team]] = []

    def add_team(team: Team) -> Optional[Team]:
        try:
            organization_id = None
            if team.affiliation is not None:
                organization_id, exists = client.add_organization(
                    contest_id=contest_id,
                    organization=AddOrganization(
                        id=str(hash(team.affiliation) % int(1e9 + 7)),
                        shortname=team.affiliation,
                        name=team.affiliation,
                        formal_name=team.affiliation,
                        country="MAR"
                    )
                )

            team_id, exists = client.add_team_to_contest(
                contest_id=contest_id,
                team_data=AddTeam(
                    id=str(hash(team.name) % int(1e9 + 7)),
                    name=f"{team.username}({team.name})",
                    display_name=team.name,
                    group_ids=["3"],
                    organization_id=organization_id
                )
            )
            team.id = team_id

            if exists:
                return

            client.add_user(
                user_data=AddUser(
                    username=team.username,
                    name=team.name,
                    password=team.password.get_secret_value(),
                    team_id=team.id,
                    roles=["team"]
                )
            )
            return team
        except Exception as e:
            print(f"[ERROR] Contest {contest_id}, team {team.name}: {e}", file=sys.stderr)
            return None

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(add_team, team) for team in teams]
        for future in as_completed(futures):
            results.append(future.result())

    return results
