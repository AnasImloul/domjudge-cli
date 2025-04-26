from typing import Union, List
import yaml
import os
import sys

from dom.infrastructure.api.domjudge import DomjudgeAPI
from dom.types.config import ProblemsConfig, Problem
from dom.core.services.problem.converter import import_problem
from dom.utils.color import get_hex_color


def apply_problems_to_contest(client: DomjudgeAPI, contest_id: str, problem_config: Union[ProblemsConfig, List[Problem]]):
    if isinstance(problem_config, ProblemsConfig):
        file_path = problem_config.from_

        if not (file_path.endswith(".yml") or file_path.endswith(".yaml")):
            print(f"[ERROR] Contest {contest_id}: Problems file '{file_path}' must be a .yml or .yaml file.",
                  file=sys.stderr)
            raise ValueError(f"Invalid file extension for problems file: {file_path}")

        if not os.path.exists(file_path):
            print(f"[ERROR] Contest {contest_id}: Problems file '{file_path}' does not exist.", file=sys.stderr)
            raise FileNotFoundError(f"Problems file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                loaded_data = yaml.safe_load(f)
                if not isinstance(loaded_data, list):
                    print(f"[ERROR] Contest {contest_id}: Problems file '{file_path}' must contain a list.",
                          file=sys.stderr)
                    raise ValueError(f"Problems file must contain a list of problems: {file_path}")
                problems = [Problem(**problem) for problem in loaded_data]
        except Exception as e:
            print(f"[ERROR] Contest {contest_id}: Failed to load problems from '{file_path}'. Error: {str(e)}",
                  file=sys.stderr)
            raise e

    elif isinstance(problem_config, list) and all(isinstance(p, Problem) for p in problem_config):
        problems = problem_config
    else:
        print(f"[ERROR] Contest {contest_id}: Invalid problem configuration.", file=sys.stderr)
        raise TypeError("Invalid problem configuration type.")

    for idx, problem in enumerate(problems, start=1):
        if not os.path.exists(problem.archive):
            raise FileNotFoundError(f"Archive not found: {problem.archive}")


    for idx, (problem, problem_package) in enumerate(
        zip(problems, [import_problem(problem) for problem in problems]),
        start=1
    ):
        try:
            # Add the problem to the contest
            client.add_problem_to_contest(contest_id, problem_package)

        except FileNotFoundError as e:
            print(f"[ERROR] Contest {contest_id}: Problem file '{problem.archive}' not found. Skipping.",
                  file=sys.stderr)
            raise e
        except Exception as e:
            print(
                f"[ERROR] Contest {contest_id}: Failed to add problem '{problem.archive}'. Unexpected error: {str(e)}",
                file=sys.stderr)

