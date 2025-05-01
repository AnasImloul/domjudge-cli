from typing import List

from typeguard import config

from .problem import load_problems_from_config
from .team import load_teams_from_config
from dom.types.config.raw import RawContestConfig
from dom.types.config.processed import ContestConfig


def load_contest_from_config(contest: RawContestConfig, config_path: str) -> ContestConfig:
    return (
        ContestConfig(
            name=contest.name,
            shortname=contest.shortname,
            formal_name=contest.formal_name,
            start_time=contest.start_time,
            duration=contest.duration,
            penalty_time=contest.penalty_time,
            allow_submit=contest.allow_submit,
            problems=load_problems_from_config(contest.problems, config_path=config_path),
            teams=load_teams_from_config(contest.teams, config_path=config_path)
        )
    )



def load_contests_from_config(contests: List[RawContestConfig], config_path: str) -> List[ContestConfig]:
    return [
        load_contest_from_config(contest, config_path)
        for contest in contests
    ]