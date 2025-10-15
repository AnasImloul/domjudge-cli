"""Declarative contest application service."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.core.services.base import ServiceContext
from dom.core.services.problem.apply import ProblemService
from dom.core.services.team.apply import TeamService
from dom.exceptions import ContestError
from dom.infrastructure.api.factory import APIClientFactory
from dom.logging_config import get_logger
from dom.types.api.models import Contest
from dom.types.config import DomConfig
from dom.types.config.processed import ContestConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class ContestApplicationService:
    """
    Declarative service for applying contest configurations.

    This service orchestrates the creation of contests and their associated
    resources (problems, teams) in a clean, declarative manner.
    """

    def __init__(self, client, secrets: SecretsProvider):
        """
        Initialize contest application service.

        Args:
            client: DOMjudge API client
            secrets: Secrets manager
        """
        self.client = client
        self.secrets = secrets
        self.problem_service = ProblemService(client)
        self.team_service = TeamService(client)

    def apply_contest(self, contest: ContestConfig) -> str:
        """
        Apply a single contest configuration.

        Args:
            contest: Contest configuration

        Returns:
            Contest ID

        Raises:
            ContestError: If contest application fails
        """
        logger.info(
            "Applying contest configuration",
            extra={"contest_name": contest.name, "contest_shortname": contest.shortname},
        )

        # Create contest
        contest_id = self._create_contest(contest)

        # Create service context for this contest
        context = ServiceContext(client=self.client, contest_id=contest_id)

        # Apply resources concurrently
        self._apply_contest_resources(contest, context)

        logger.info(
            f"Successfully configured contest '{contest.shortname}'",
            extra={
                "contest_id": contest_id,
                "contest_shortname": contest.shortname,
                "problems_count": len(contest.problems),
                "teams_count": len(contest.teams),
            },
        )

        return contest_id

    def _create_contest(self, contest: ContestConfig) -> str:
        """
        Create or get contest.

        Args:
            contest: Contest configuration

        Returns:
            Contest ID
        """
        try:
            result = self.client.contests.create(
                contest_data=Contest(
                    name=contest.name or contest.shortname,  # type: ignore[arg-type]
                    shortname=contest.shortname,  # type: ignore[arg-type]
                    formal_name=contest.formal_name or contest.name,
                    start_time=contest.start_time,
                    duration=contest.duration,
                    allow_submit=contest.allow_submit,
                )
            )

            action = "Created" if result.created else "Found existing"
            logger.info(
                f"{action} contest",
                extra={
                    "contest_id": result.id,
                    "contest_shortname": contest.shortname,
                    "created": result.created,
                },
            )

            return str(result.id)

        except Exception as e:
            logger.error(
                f"Failed to create/get contest '{contest.shortname}'",
                exc_info=True,
                extra={"contest_shortname": contest.shortname},
            )
            raise ContestError(f"Failed to create/get contest '{contest.shortname}': {e}") from e

    def _apply_contest_resources(self, contest: ContestConfig, context: ServiceContext) -> None:
        """
        Apply problems and teams to contest concurrently.

        Args:
            contest: Contest configuration
            context: Service context

        Raises:
            ContestError: If resource application fails
        """
        exceptions = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit concurrent tasks
            future_to_task = {
                executor.submit(self._apply_problems, contest.problems, context): "problems",
                executor.submit(self._apply_teams, contest.teams, context): "teams",
            }

            # Collect results
            for future in as_completed(future_to_task.keys()):
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
                            "contest_id": context.contest_id,
                        },
                    )
                    exceptions.append((task_name, e))

        if exceptions:
            error_details = ", ".join([f"{task}: {e!s}" for task, e in exceptions])
            raise ContestError(
                f"Failed to fully configure contest '{contest.shortname}': {error_details}"
            )

    def _apply_problems(self, problems, context: ServiceContext) -> None:
        """Apply problems using problem service."""
        results = self.problem_service.create_many(problems, context, stop_on_error=False)

        summary = self.problem_service.get_summary(results)
        if summary["failed"] > 0:
            raise ContestError(f"{summary['failed']} problem(s) failed to add")

    def _apply_teams(self, teams, context: ServiceContext) -> None:
        """Apply teams using team service."""
        results = self.team_service.create_many(teams, context, stop_on_error=False)

        summary = self.team_service.get_summary(results)
        if summary["failed"] > 0:
            raise ContestError(f"{summary['failed']} team(s) failed to add")


def apply_contests(config: DomConfig, secrets: SecretsProvider) -> None:
    """
    Apply contest configurations to DOMjudge platform.

    Args:
        config: Complete DOMjudge configuration
        secrets: Secrets manager for retrieving credentials

    Raises:
        ContestError: If contest application fails
    """
    factory = APIClientFactory()
    client = factory.create_admin_client(config.infra, secrets)

    service = ContestApplicationService(client, secrets)

    for contest in config.contests:
        service.apply_contest(contest)
