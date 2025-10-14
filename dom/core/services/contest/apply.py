"""Contest application service."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.core.services.problem.apply import apply_problems_to_contest
from dom.core.services.team.apply import apply_teams_to_contest
from dom.exceptions import ContestError
from dom.infrastructure.api.factory import APIClientFactory
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
from dom.types.api.models import Contest
from dom.types.config import DomConfig

logger = get_logger(__name__)


def apply_contests(config: DomConfig, secrets: SecretsManager):
    """
    Apply contest configuration to DOMjudge platform.

    Args:
        config: Complete DOMjudge configuration
        secrets: Secrets manager for retrieving credentials

    Raises:
        ContestError: If contest creation or configuration fails
    """
    factory = APIClientFactory()
    client = factory.create_admin_client(config.infra, secrets)

    for contest in config.contests:
        logger.info(
            "Applying contest configuration",
            extra={"contest_name": contest.name, "contest_shortname": contest.shortname},
        )

        try:
            result = client.contests.create(
                contest_data=Contest(
                    name=contest.name or contest.shortname,  # type: ignore[arg-type]
                    shortname=contest.shortname,  # type: ignore[arg-type]
                    formal_name=contest.formal_name or contest.name,
                    start_time=contest.start_time,
                    duration=contest.duration,
                    allow_submit=contest.allow_submit,
                )
            )

            contest_id = result.id
            action = "Created" if result.created else "Found existing"
            logger.info(
                f"{action} contest",
                extra={
                    "contest_id": contest_id,
                    "contest_shortname": contest.shortname,
                    "created": result.created,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to create/get contest '{contest.shortname}'",
                exc_info=True,
                extra={"contest_shortname": contest.shortname},
            )
            raise ContestError(f"Failed to create/get contest '{contest.shortname}': {e}") from e

        # Apply problems and teams concurrently
        exceptions = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_task = {
                executor.submit(
                    apply_problems_to_contest, client, contest_id, contest.problems
                ): "problems",
                executor.submit(apply_teams_to_contest, client, contest_id, contest.teams): "teams",
            }

            for future in as_completed(future_to_task.keys()):  # type: ignore[var-annotated, arg-type]
                task_name = future_to_task[future]
                try:
                    future.result()
                    logger.info(f"Successfully applied {task_name} for contest {contest.shortname}")
                except Exception as e:
                    logger.error(
                        f"Failed to apply {task_name} for contest {contest.shortname}",
                        exc_info=True,
                        extra={
                            "task": task_name,
                            "contest_shortname": contest.shortname,
                            "contest_id": contest_id,
                        },
                    )
                    exceptions.append((task_name, e))

        if exceptions:
            error_details = ", ".join([f"{task}: {e!s}" for task, e in exceptions])
            raise ContestError(
                f"Failed to fully configure contest '{contest.shortname}': {error_details}"
            )

        logger.info(
            f"Successfully configured contest '{contest.shortname}'",
            extra={
                "contest_id": contest_id,
                "contest_shortname": contest.shortname,
                "problems_count": len(contest.problems),
                "teams_count": len(contest.teams),
            },
        )
