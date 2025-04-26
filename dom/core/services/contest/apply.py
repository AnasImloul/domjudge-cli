from dom.types.config import DomConfig
from dom.infrastructure.api.domjudge import DomjudgeAPI
from dom.infrastructure.secrets.manager import load_secret
from dom.types.api.models import Contest
from dom.core.services.problem.apply import apply_problems_to_contest
from dom.core.services.team.apply import apply_teams_to_contest


def apply_contests(config: DomConfig):

    client = DomjudgeAPI(
        base_url=f"http://localhost:{config.infra.port}",
        username="admin",
        password=load_secret("admin_password")
    )

    for contest in config.contests:
        contest_id, created = client.create_contest(
            contest_data=Contest(
                name=contest.name or contest.shortname,
                shortname=contest.shortname,
                formal_name=contest.formal_name or contest.name,
                start_time=contest.start_time,
                duration=contest.duration,
                allow_submit=contest.allow_submit
            )
        )

        apply_problems_to_contest(client, contest_id, contest.problems)

        apply_teams_to_contest(client, contest_id, contest.teams)


