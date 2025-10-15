import csv
import re
from pathlib import Path

from dom.logging_config import get_logger
from dom.types.config.raw import RawTeamsConfig
from dom.types.secrets import SecretsProvider
from dom.types.team import Team

logger = get_logger(__name__)


def read_teams_file(file_path: Path, delimiter: str | None = None) -> list[list[str]]:
    if not file_path.exists():
        raise FileNotFoundError(f"Teams file not found: {file_path}")

    ext = file_path.suffix.lstrip(".").lower()
    if ext not in ("csv", "tsv"):
        raise ValueError(f"Unsupported file extension '{ext}'. Only .csv and .tsv are allowed.")

    delimiter = delimiter or ("," if ext == "csv" else "\t")

    teams = []
    with file_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if any(cell.strip() for cell in row):
                teams.append([cell.strip() for cell in row])
    return teams


def parse_from_template(template: str, row: list[str]) -> str:
    def replacer(match):
        index = int(match.group(1)) - 1
        if index < 0 or index >= len(row):
            raise IndexError(f"Placeholder '${index + 1}' is out of range for row: {row}")
        return row[index]

    pattern = re.compile(r"\$(\d+)")
    name = pattern.sub(replacer, template)
    return name


def load_teams_from_config(
    team_config: RawTeamsConfig, config_path: Path, secrets: SecretsProvider
):
    """
    Load teams from configuration file.

    Args:
        team_config: Raw team configuration
        config_path: Path to config file for relative path resolution
        secrets: Secrets manager for generating deterministic passwords

    Returns:
        List of Team objects
    """
    # Resolve file_path relative to the directory of config_path
    config_dir = config_path.resolve().parent
    file_path = config_dir / team_config.from_

    file_format = file_path.suffix.lstrip(".").lower()

    if file_format not in ("csv", "tsv"):
        logger.error(f"Teams file '{file_path}' must be a .csv or .tsv file")
        raise ValueError(f"Invalid file extension for teams file: {file_path}")

    if not file_path.exists():
        logger.error(f"Teams file '{file_path}' does not exist")
        raise FileNotFoundError(f"Teams file not found: {file_path}")

    try:
        teams_data = read_teams_file(file_path, delimiter=team_config.delimiter)
    except Exception as e:
        logger.error(f"Failed to load teams from '{file_path}': {e}")
        raise e

    row_range = team_config.rows
    if row_range:
        start, end = map(int, row_range.split("-"))
        teams_data = teams_data[start - 1 : end]

    teams = []

    for idx, row in enumerate(teams_data, start=1):
        try:
            team_name = parse_from_template(team_config.name, row).strip()
            affiliation = (
                parse_from_template(team_config.affiliation, row).strip()
                if team_config.affiliation.strip()
                else None
            )
            teams.append(
                Team(
                    name=team_name,
                    password=secrets.generate_deterministic_password(
                        seed=team_name.strip(), length=10
                    ),
                    affiliation=affiliation.strip() or None,  # type: ignore[union-attr]
                )
            )

        except Exception as e:
            logger.error(f"Failed to prepare team from row {idx}: {e}")
            raise e

    # Validate no duplicate team names
    team_names = [team.name for team in teams]
    if len(team_names) != len(set(team_names)):
        duplicates = {name for name in team_names if team_names.count(name) > 1}
        raise ValueError(f"Duplicate team names detected: {', '.join(duplicates)}")

    logger.info(f"Loaded {len(teams)} teams from {file_path}")
    return teams
