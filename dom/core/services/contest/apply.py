"""Declarative contest application service."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from dom.core.services.base import OrchestratorService, ServiceContext
from dom.core.services.contest.state import ChangeType, ContestStateComparator
from dom.core.services.problem.apply import ProblemService
from dom.core.services.team.apply import TeamService
from dom.exceptions import ContestError
from dom.infrastructure.api.factory import APIClientFactory
from dom.logging_config import console, get_logger
from dom.types.api.models import Contest
from dom.types.config import DomConfig
from dom.types.config.processed import ContestConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


class ContestApplicationService(OrchestratorService):
    """
    Orchestrator service for applying contest configurations.

    Inherits from OrchestratorService to provide a consistent pattern for
    services that coordinate multiple entity services.

    Architecture Pattern: Orchestrator Service
    - Coordinates ProblemService, TeamService, and ContestStateComparator
    - Implements complex multi-step workflows
    - Handles cross-cutting concerns (error handling, concurrency)
    - Provides high-level business operations

    This service orchestrates the creation of contests and their associated
    resources (problems, teams) in a clean, declarative manner.
    """

    def __init__(self, client, infra_config, secrets: SecretsProvider):
        """
        Initialize contest application service.

        Args:
            client: DOMjudge API client
            infra_config: Infrastructure configuration
            secrets: Secrets manager
        """
        super().__init__(client)
        self.infra_config = infra_config
        self.secrets = secrets
        self.problem_service = ProblemService(client)
        self.team_service = TeamService(client)
        self.state_comparator = ContestStateComparator(infra_config, secrets, client)

    def apply_contest(self, contest: ContestConfig) -> str:
        """
        Apply a single contest configuration.

        This method is idempotent and safe for INITIAL SETUP only:
        - If contest doesn't exist, creates it
        - If contest exists, SKIPS contest fields (cannot be updated via API)
        - Resources (problems/teams) are always applied idempotently

        IMPORTANT: DOMjudge API does NOT support updating contests.
        This tool is designed for INITIAL SETUP only. Once contests are created,
        any changes to contest fields must be made manually via the DOMjudge web UI.

        Args:
            contest: Contest configuration

        Returns:
            Contest ID

        Raises:
            ContestError: If contest application fails
        """
        logger.info(
            "Applying contest configuration",
            extra={
                "contest_name": contest.name,
                "contest_shortname": contest.shortname,
            },
        )

        # Detect changes first
        change_set = self.state_comparator.compare(contest)

        # Create or skip contest
        if change_set.change_type == ChangeType.CREATE:
            contest_id = self._create_contest(contest)
            logger.info(f"✓ Created new contest '{contest.shortname}' (ID: {contest_id})")
        else:
            # Get existing contest
            assert contest.shortname is not None, "Contest shortname is required"
            current = self.state_comparator._fetch_current_state(contest.shortname)
            assert current is not None, f"Contest '{contest.shortname}' should exist at this point"
            contest_id = current["id"]

            # Show warning if there are field changes
            if change_set.field_changes:
                changed_fields = ", ".join([fc.field for fc in change_set.field_changes])
                console.print(f"\n[yellow]⚠ Contest '{contest.shortname}' already exists[/yellow]")
                console.print(f"[yellow]  Changed fields detected: {changed_fields}[/yellow]")
                console.print(
                    "[yellow]  → DOMjudge API does not support updating contests[/yellow]"
                )
                console.print(
                    "[yellow]  → Please update manually in DOMjudge web UI (Jury > Contests)[/yellow]\n"
                )

                logger.warning(
                    f"Contest '{contest.shortname}' exists with field changes that cannot be applied via API",
                    extra={
                        "contest_id": contest_id,
                        "changed_fields": changed_fields,
                    },
                )
            else:
                logger.info(f"✓ Contest '{contest.shortname}' exists with no field changes")

        # Create contest-specific team group for scoreboard filtering
        shortname = contest.shortname or "contest"
        group_name = f"{shortname.upper()} Teams"
        group_result = self.client.groups.create_for_contest(
            contest_id=contest_id, name=group_name, group_id=f"{shortname}-teams"
        )
        team_group_id = group_result.id

        logger.info(
            f"Created team group '{group_name}' (ID: {team_group_id}) for contest {contest.shortname}"
        )

        # Create service context for this contest with the group
        context = ServiceContext(
            client=self.client,
            contest_id=contest_id,
            contest_shortname=contest.shortname,
            team_group_id=team_group_id,
        )

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
                    "was_created": result.created,
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

    service = ContestApplicationService(client, config.infra, secrets)

    for contest in config.contests:
        service.apply_contest(contest)
