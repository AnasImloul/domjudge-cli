from typing import List
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.types.problem import ProblemPackage

def apply_problems_to_contest(client: DomJudgeAPI, contest_id: str, problem_packages: List[ProblemPackage]):
    def add_problem(problem_package: ProblemPackage):
        try:
            problem_id = client.add_problem_to_contest(contest_id, problem_package)
            problem_package.id = problem_id
        except Exception as e:
            print(
                f"[ERROR] Contest {contest_id}: Failed to add problem '{problem_package.yaml.name}'. Unexpected error: {str(e)}",
                file=sys.stderr,
            )

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(add_problem, problem_package) for problem_package in problem_packages]

        for future in as_completed(futures):
            # This ensures exceptions in threads are not silently ignored
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] Unexpected exception during problem addition: {str(e)}", file=sys.stderr)
