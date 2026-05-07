"""Declarative contest application service.

The orchestrator (:meth:`ContestApplicationService.apply_contest`) reads
top-down as a sequence of named steps. Each step is implemented as a
small, single-purpose private method below the orchestrator.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from dom.core.services.base import ServiceContext
from dom.core.services.contest.changes import ChangeType, ContestChangeSet, FieldChange
from dom.core.services.contest.state import ContestStateComparator
from dom.core.services.problem.apply import ProblemService
from dom.core.services.protocols import DomJudgeAPIProtocol
from dom.core.services.team.apply import TeamService
from dom.exceptions import ContestError
from dom.logging_config import get_logger
from dom.types.api.models import Contest
from dom.types.config.processed import ContestConfig
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)


@dataclass(frozen=True)
class ContestApplyResult:
    """Outcome of applying a single contest.

    ``skipped_field_changes`` lists field deltas that were detected on an
    existing contest but could not be applied (DOMjudge API does not
    support contest updates). The CLI layer renders these to the user;
    the service stays free of presentation concerns.
    """

    contest_shortname: str
    contest_id: str
    skipped_field_changes: list[FieldChange] = field(default_factory=list)


class ContestApplicationService:
    """Declarative service for applying contest configurations.

    Idempotent and intended for INITIAL SETUP only. The DOMjudge API
    does not support contest updates: if a contest already exists with
    different fields, the deltas are surfaced via
    :class:`ContestApplyResult.skipped_field_changes` rather than applied.
    Resources (problems, teams) are always reconciled idempotently.
    """

    def __init__(
        self,
        client: DomJudgeAPIProtocol,
        secrets: SecretsProvider,
        *,
        problem_service: ProblemService | None = None,
        team_service: TeamService | None = None,
        state_comparator: ContestStateComparator | None = None,
    ):
        self.client = client
        self.secrets = secrets
        self.problem_service = problem_service or ProblemService(client)
        self.team_service = team_service or TeamService(client)
        self.state_comparator = state_comparator or ContestStateComparator(client)

    # ------------------------------------------------------------------ public

    def apply_contest(self, contest: ContestConfig) -> ContestApplyResult:
        """Apply a single contest configuration.

        Reads top-down as a sequence of steps:
        compare → create-or-resolve → provision team group → apply resources.
        """
        shortname = _require_shortname(contest)
        logger.info(
            "Applying contest configuration",
            extra={"contest_name": contest.name, "contest_shortname": shortname},
        )

        change_set = self.state_comparator.compare_contest(contest)
        contest_id, skipped = self._resolve_or_create(contest, change_set)
        team_group_id = self._provision_team_group(contest_id, shortname)

        self._apply_resources(
            contest,
            ServiceContext(
                client=self.client,
                contest_id=contest_id,
                contest_shortname=shortname,
                team_group_id=team_group_id,
            ),
        )

        logger.info(
            f"Successfully configured contest '{shortname}'",
            extra={
                "contest_id": contest_id,
                "contest_shortname": shortname,
                "problems_count": len(contest.problems),
                "teams_count": len(contest.teams),
            },
        )
        return ContestApplyResult(
            contest_shortname=shortname,
            contest_id=contest_id,
            skipped_field_changes=skipped,
        )

    # ------------------------------------------------------------------ steps

    def _resolve_or_create(
        self, contest: ContestConfig, change_set: ContestChangeSet
    ) -> tuple[str, list[FieldChange]]:
        """Return ``(contest_id, skipped_field_changes)`` for the contest.

        Creates a new contest when the change set says so; otherwise
        resolves the existing one and reports any field deltas that
        cannot be applied via the API.
        """
        shortname = change_set.contest_shortname

        if change_set.change_type == ChangeType.CREATE:
            contest_id = self._create_contest(contest)
            logger.info(f"✓ Created new contest '{shortname}' (ID: {contest_id})")
            return contest_id, []

        contest_id = self._resolve_existing_contest_id(shortname)

        if not change_set.field_changes:
            logger.info(f"✓ Contest '{shortname}' exists with no field changes")
            return contest_id, []

        skipped = list(change_set.field_changes)
        logger.warning(
            f"Contest '{shortname}' exists with field changes that cannot be applied via API",
            extra={
                "contest_id": contest_id,
                "changed_fields": ", ".join(fc.field for fc in skipped),
            },
        )
        return contest_id, skipped

    def _resolve_existing_contest_id(self, shortname: str) -> str:
        current = self.state_comparator._fetch_current_contest(shortname)
        if current is None:
            raise ContestError(
                f"Contest '{shortname}' was expected to exist but could not be fetched"
            )
        return str(current["id"])

    def _create_contest(self, contest: ContestConfig) -> str:
        shortname = _require_shortname(contest)
        try:
            result = self.client.contests.create(
                contest_data=Contest(
                    name=contest.name or shortname,
                    shortname=shortname,
                    formal_name=contest.formal_name or contest.name,
                    start_time=contest.start_time,
                    duration=contest.duration,
                    allow_submit=contest.allow_submit,
                )
            )
        except Exception as exc:
            logger.error(
                f"Failed to create/get contest '{shortname}'",
                exc_info=True,
                extra={"contest_shortname": shortname},
            )
            raise ContestError(f"Failed to create/get contest '{shortname}': {exc}") from exc

        action = "Created" if result.created else "Found existing"
        logger.info(
            f"{action} contest",
            extra={
                "contest_id": result.id,
                "contest_shortname": shortname,
                "was_created": result.created,
            },
        )
        return str(result.id)

    def _provision_team_group(self, contest_id: str, shortname: str) -> str:
        """Create the contest-specific team group used for scoreboard filtering."""
        group_name = f"{shortname.upper()} Teams"
        result = self.client.groups.create_for_contest(
            contest_id=contest_id, name=group_name, group_id=f"{shortname}-teams"
        )
        logger.info(f"Created team group '{group_name}' (ID: {result.id}) for contest {shortname}")
        return str(result.id)

    def _apply_resources(self, contest: ContestConfig, context: ServiceContext) -> None:
        """Apply problems and teams concurrently, collecting any failures."""
        tasks: dict[str, Callable[[], None]] = {
            "problems": lambda: self._apply_problems(contest.problems, context),
            "teams": lambda: self._apply_teams(contest.teams, context),
        }
        failures = _run_concurrent(tasks, context, contest.shortname or "?")
        if failures:
            details = ", ".join(f"{name}: {exc!s}" for name, exc in failures)
            raise ContestError(
                f"Failed to fully configure contest '{contest.shortname}': {details}"
            )

    def _apply_problems(self, problems, context: ServiceContext) -> None:
        results = self.problem_service.create_many(problems, context, stop_on_error=False)
        summary = self.problem_service.get_summary(results)
        if summary["failed"] > 0:
            raise ContestError(f"{summary['failed']} problem(s) failed to add")

    def _apply_teams(self, teams, context: ServiceContext) -> None:
        results = self.team_service.create_many(teams, context, stop_on_error=False)
        summary = self.team_service.get_summary(results)
        if summary["failed"] > 0:
            raise ContestError(f"{summary['failed']} team(s) failed to add")


# ---------------------------------------------------------------- helpers


def _require_shortname(contest: ContestConfig) -> str:
    """Treat shortname as a precondition. Loaders must guarantee it."""
    if contest.shortname is None:
        raise ContestError("Contest configuration is missing required 'shortname'")
    return contest.shortname


def _run_concurrent(
    tasks: dict[str, Callable[[], None]],
    context: ServiceContext,
    contest_shortname: str,
) -> list[tuple[str, Exception]]:
    """Run named tasks in parallel, returning ``(name, exc)`` for each failure.

    All tasks run to completion even if some fail, so the caller sees
    every problem at once instead of fixing them one round-trip at a time.
    """
    failures: list[tuple[str, Exception]] = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as exc:
                logger.error(
                    f"Failed to apply {name} for contest {contest_shortname}",
                    exc_info=True,
                    extra={
                        "task": name,
                        "contest_shortname": contest_shortname,
                        "contest_id": context.contest_id,
                    },
                )
                failures.append((name, exc))
            else:
                logger.info(f"Successfully applied {name} for contest {contest_shortname}")
    return failures
