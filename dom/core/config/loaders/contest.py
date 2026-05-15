from pathlib import Path

from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig
from dom.types.config.raw import RawContestConfig
from dom.types.secrets import SecretsProvider
from dom.utils.hashing import generate_team_username
from dom.utils.problem import assign_problem_letters

from .problem import load_problems_from_config
from .team import load_teams_from_config

logger = get_logger(__name__)


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
    problems = load_problems_from_config(raw_contest.problems, config_path=config_path)
    teams = load_teams_from_config(
        raw_contest.teams,
        config_path=config_path,
        secrets=secrets,
    )

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
    # Process all contests - problems are loaded within contest loading
    processed_contests = [
        load_contest_from_config(contest, config_path, secrets) for contest in raw_contests
    ]

    # Assign usernames and passwords to teams.
    # Usernames must be globally unique across all contests. The base hash
    # has only 10000 buckets, so collisions are likely (birthday paradox:
    # ~14% for 55 teams). Track assigned usernames and probe deterministically
    # by appending a collision counter to the seed until we land on a free one.
    used_usernames: set[str] = set()
    for contest in processed_contests:
        contest.teams.sort(key=lambda team: team.name)

        for team in contest.teams:
            team.username = _assign_unique_team_username(
                secrets, team.composite_key, used_usernames
            )
            used_usernames.add(team.username)

            team.password = secrets.generate_deterministic_password(
                seed=team.composite_key, length=10
            )

    return processed_contests


def _assign_unique_team_username(
    secrets: SecretsProvider, composite_key: str, used: set[str]
) -> str:
    """Deterministically pick a free ``team####`` handle.

    Re-hashes ``composite_key`` with an incrementing collision suffix until
    the result is not already in ``used``. Stable across runs as long as the
    sorted team list is stable.
    """
    attempt = 0
    while True:
        seed = composite_key if attempt == 0 else f"{composite_key}#collision{attempt}"
        username = generate_team_username(secrets, seed)
        if username not in used:
            return username
        attempt += 1
