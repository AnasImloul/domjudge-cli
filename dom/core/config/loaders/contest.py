from itertools import chain
from pathlib import Path

from dom.types.config.processed import ContestConfig
from dom.types.config.raw import RawContestConfig
from dom.types.secrets import SecretsProvider
from dom.types.team import Team
from dom.utils.problem import assign_problem_letters

from .problem import load_problems_from_config
from .team import load_teams_from_config


def load_contest_from_config(
    raw_contest: RawContestConfig, config_path: Path, secrets: SecretsProvider
) -> ContestConfig:
    """
    Load contest configuration from raw config.

    Args:
        raw_contest: Raw contest configuration
        config_path: Path to config file
        secrets: Secrets manager for team password generation

    Returns:
        Processed contest configuration
    """
    # Load problems and teams
    problems = load_problems_from_config(
        raw_contest.problems, with_statement=raw_contest.with_statement, config_path=config_path
    )
    teams = load_teams_from_config(raw_contest.teams, config_path=config_path, secrets=secrets)

    # Assign problem letters (A, B, C, ...) - creates new immutable objects
    problems_with_letters = assign_problem_letters(problems)

    # Create processed contest configuration
    processed_contest = ContestConfig(
        name=raw_contest.name,
        shortname=raw_contest.shortname,
        formal_name=raw_contest.formal_name,
        start_time=raw_contest.start_time,
        duration=raw_contest.duration,
        penalty_time=raw_contest.penalty_time,
        allow_submit=raw_contest.allow_submit,
        with_statement=raw_contest.with_statement,
        problems=problems_with_letters,
        teams=teams,
    )

    return processed_contest


def load_contests_from_config(
    raw_contests: list[RawContestConfig], config_path: Path, secrets: SecretsProvider
) -> list[ContestConfig]:
    """
    Load all contests from raw configuration.

    Args:
        raw_contests: List of raw contest configurations
        config_path: Path to config file
        secrets: Secrets manager for team password generation

    Returns:
        List of processed contest configurations
    """
    # Process all contests
    processed_contests = [
        load_contest_from_config(contest, config_path, secrets) for contest in raw_contests
    ]

    # Combine teams from all contests for consistent numbering
    combined_teams: list[Team] = list(
        chain.from_iterable([contest.teams for contest in processed_contests])
    )

    # Sort and assign sequential usernames
    combined_teams.sort(key=lambda team: team.name)

    for idx, team in enumerate(combined_teams, start=1):
        team.username = f"Team_{idx}"

    return processed_contests
