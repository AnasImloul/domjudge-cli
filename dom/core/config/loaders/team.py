from typing import List
import os
import sys
import csv
import re

from dom.types.config.raw import RawTeamsConfig
from dom.types.team import Team
from dom.infrastructure.secrets import generate_secure_password


def read_teams_file(file_path: str, delimiter: str = None) -> List[List[str]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Teams file not found: {file_path}")

    ext = file_path.split(".")[-1].lower()
    if ext not in ("csv", "tsv"):
        raise ValueError(f"Unsupported file extension '{ext}'. Only .csv and .tsv are allowed.")

    delimiter = delimiter or ("," if ext == "csv" else "\t")

    teams = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if any(cell.strip() for cell in row):
                teams.append([cell.strip() for cell in row])
    return teams

def parse_from_template(template: str, row: List[str]) -> str:
    def replacer(match):
        index = int(match.group(1)) - 1
        if index < 0 or index >= len(row):
            raise IndexError(f"Placeholder '${index + 1}' is out of range for row: {row}")
        return row[index]

    pattern = re.compile(r'\$(\d+)')
    name = pattern.sub(replacer, template)
    return name

def load_teams_from_config(team_config: RawTeamsConfig, config_path: str):
    file_path = team_config.from_

    # Resolve file_path relative to the directory of config_path
    config_dir = os.path.dirname(os.path.abspath(config_path))
    file_path = os.path.join(config_dir, file_path)

    file_format = file_path.split(".")[-1]

    if file_format not in ("csv", "tsv"):
        print(f"[ERROR] Teams file '{file_path}' must be a .csv or .tsv file.", file=sys.stderr)
        raise ValueError(f"Invalid file extension for teams file: {file_path}")

    if not os.path.exists(file_path):
        print(f"[ERROR] Teams file '{file_path}' does not exist.", file=sys.stderr)
        raise FileNotFoundError(f"Teams file not found: {file_path}")

    try:
        teams_data = read_teams_file(file_path, delimiter=team_config.delimiter)
    except Exception as e:
        print(f"[ERROR] Failed to load teams from '{file_path}'. Error: {str(e)}", file=sys.stderr)
        raise e

    row_range = team_config.rows
    if row_range:
        start, end = map(int, row_range.split("-"))
        teams_data = teams_data[start - 1:end]

    teams = []

    for idx, row in enumerate(teams_data, start=1):
        try:
            team_name = parse_from_template(team_config.name, row).strip()
            affiliation = parse_from_template(team_config.affiliation, row).strip() if team_config.affiliation.strip() else None
            teams.append(
                Team(
                    name=team_name,
                    password=generate_secure_password(length=10, seed=team_name.strip()),
                    affiliation=affiliation.strip() or None
                )
            )

        except Exception as e:
            print(f"[ERROR] Failed to prepare team from row {idx}. Unexpected error: {str(e)}", file=sys.stderr)

    # Validate no duplicate team names
    team_names = [team.name for team in teams]
    if len(team_names) != len(set(team_names)):
        duplicates = set(name for name in team_names if team_names.count(name) > 1)
        raise ValueError(f"Duplicate team names detected: {', '.join(duplicates)}")

    return teams
