from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.constants import MAX_CONCURRENT_PROBLEM_OPERATIONS
from dom.exceptions import APIError, ProblemError
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.logging_config import get_logger
from dom.types.problem import ProblemPackage

logger = get_logger(__name__)


def apply_problems_to_contest(
    client: DomJudgeAPI, contest_id: str, problem_packages: list[ProblemPackage]
) -> None:
    """
    Apply problems to a contest with proper error handling.

    Args:
        client: DOMjudge API client
        contest_id: Contest identifier
        problem_packages: List of problem packages to add

    Raises:
        ProblemError: If one or more problems fail to add
    """

    def add_problem(problem_package: ProblemPackage):
        try:
            problem_id = client.problems.add_to_contest(contest_id, problem_package)
            problem_package.id = problem_id
            logger.info(
                "Successfully added problem to contest",
                extra={
                    "problem_name": problem_package.yaml.name,
                    "problem_id": problem_id,
                    "contest_id": contest_id,
                },
            )
        except APIError as e:
            logger.error(
                f"Failed to add problem '{problem_package.yaml.name}' to contest {contest_id}",
                exc_info=True,
                extra={
                    "problem_name": problem_package.yaml.name,
                    "contest_id": contest_id,
                    "error_type": type(e).__name__,
                },
            )
            raise ProblemError(f"Failed to add problem '{problem_package.yaml.name}': {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error adding problem '{problem_package.yaml.name}' to contest {contest_id}",
                exc_info=True,
                extra={
                    "problem_name": problem_package.yaml.name,
                    "contest_id": contest_id,
                    "error_type": type(e).__name__,
                },
            )
            raise ProblemError(
                f"Unexpected error adding problem '{problem_package.yaml.name}': {e}"
            ) from e

    exceptions = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PROBLEM_OPERATIONS) as executor:
        futures = [
            executor.submit(add_problem, problem_package) for problem_package in problem_packages
        ]

        for future in as_completed(futures):
            try:
                future.result()
            except ProblemError as e:
                exceptions.append(e)
                logger.error(f"Problem addition task failed: {e}")
            except Exception as e:
                exceptions.append(e)  # type: ignore[arg-type]
                logger.error(f"Unexpected exception in problem addition task: {e}", exc_info=True)

    if exceptions:
        error_summary = f"{len(exceptions)} problem(s) failed to add out of {len(problem_packages)}"
        logger.error(error_summary)
        raise ProblemError(error_summary)
