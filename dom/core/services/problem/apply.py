from typing import List
import sys

from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.types.problem import ProblemPackage


def apply_problems_to_contest(client: DomJudgeAPI, contest_id: str, problem_packages: List[ProblemPackage]):
    for idx, problem_package in enumerate(problem_packages, start=1):
        try:
            # Add the problem to the contest
            client.add_problem_to_contest(contest_id, problem_package)
        except Exception as e:
            print(
                f"[ERROR] Contest {contest_id}: Failed to add problem '{problem_package.yaml.name}'. Unexpected error: {str(e)}",
                file=sys.stderr)
