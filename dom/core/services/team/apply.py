from typing import Union, List
import yaml
import os
import sys
import csv
import re


from dom.infrastructure.api.domjudge import DomjudgeAPI
from dom.types.config import TeamsConfig
from dom.types.api.models import AddTeam, AddUser
from dom.infrastructure.secrets import generate_secure_password
from dom.utils.unicode import clean_team_name

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

def generate_team_name(template: str, row: List[str]) -> str:
    def replacer(match):
        index = int(match.group(1)) - 1
        if index < 0 or index >= len(row):
            raise IndexError(f"Placeholder '${index + 1}' is out of range for row: {row}")
        return row[index]

    pattern = re.compile(r'\$(\d+)')
    name = pattern.sub(replacer, template)
    return name

def apply_teams_to_contest(client: DomjudgeAPI, contest_id: str, team_config: TeamsConfig):

    file_path = team_config.from_

    file_format = file_path.split(".")[-1]

    if not (file_format in ("csv", "tsv")):
        print(f"[ERROR] Contest {contest_id}: Teams file '{file_path}' must be a .csv or .tsv file.",
              file=sys.stderr)
        raise ValueError(f"Invalid file extension for teams file: {file_path}")

    if not os.path.exists(file_path):
        print(f"[ERROR] Contest {contest_id}: Teams file '{file_path}' does not exist.", file=sys.stderr)
        raise FileNotFoundError(f"Teams file not found: {file_path}")

    try:
        teams_data = read_teams_file(file_path, delimiter=team_config.delimiter)
    except Exception as e:
        print(f"[ERROR] Contest {contest_id}: Failed to load teams from '{file_path}'. Error: {str(e)}",
              file=sys.stderr)
        raise e

    row_range = team_config.rows
    if row_range:
        start, end = map(int, row_range.split("-"))
        teams_data = teams_data[start - 1:end]

    for idx, row in enumerate(teams_data, start=1):
        try:
            team_name = generate_team_name(team_config.name, row)
            highest_id = max([int(team["id"]) for team in client.list_contest_teams(contest_id)])
            team_id = client.add_team_to_contest(
                contest_id=contest_id,
                team_data=AddTeam(
                    id=str(highest_id + 1),
                    name=clean_team_name(team_name, allow_spaces=False),
                    display_name=team_name,
                    group_ids=["3"],
                )
            )

            user_id = client.add_user(
                user_data=AddUser(
                    username=clean_team_name(team_name, allow_spaces=False),
                    name=clean_team_name(team_name, allow_spaces=False),
                    password=generate_secure_password(length=10, seed=team_name),
                    team_id=team_id,
                    roles=[
                        "team"
                    ]
                )
            )

        except Exception as e:
            print(f"[ERROR] Contest {contest_id}: Failed to prepare team from row {idx}. Unexpected error: {str(e)}",
                  file=sys.stderr)
