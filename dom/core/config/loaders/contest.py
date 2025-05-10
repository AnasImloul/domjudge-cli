from typing import List
from itertools import chain
from typeguard import config

from .problem import load_problems_from_config
from .team import load_teams_from_config
from dom.types.config.raw import RawContestConfig
from dom.types.config.processed import ContestConfig
from dom.types.team import Team


def load_contest_from_config(contest: RawContestConfig, config_path: str) -> ContestConfig:
    contest = ContestConfig(
        name=contest.name,
        shortname=contest.shortname,
        formal_name=contest.formal_name,
        start_time=contest.start_time,
        duration=contest.duration,
        penalty_time=contest.penalty_time,
        allow_submit=contest.allow_submit,
        with_statement=contest.with_statement,
        problems=load_problems_from_config(
            contest.problems,
            with_statement=contest.with_statement,
            config_path=config_path
        ),
        teams=load_teams_from_config(contest.teams, config_path=config_path)
    )

    for i, problem in enumerate(contest.problems):
        problem.yaml.name = chr(ord("A") + i)
        problem.ini.externalid = chr(ord("A") + i)
        problem.ini.short_name = chr(ord("A") + i)

    return contest


def load_contests_from_config(contests: List[RawContestConfig], config_path: str) -> List[ContestConfig]:
    contests = [
        load_contest_from_config(contest, config_path)
        for contest in contests
    ]

    combined_teams: List[Team] = list(chain.from_iterable([contest.teams for contest in contests]))

    combined_teams.sort(key=lambda team: team.name)

    for idx, team in enumerate(combined_teams, start=1):
        team.username = f"Team_{idx}"

    return contests