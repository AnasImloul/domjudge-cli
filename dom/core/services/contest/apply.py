"""Contest application toolkit.

This service is intentionally a flat collection of single-purpose
methods. The orchestration that turns these methods into a workflow
lives one layer up, in :mod:`dom.core.operations.contest.apply`, where
each step is named and executed via the operations framework. Keeping
the orchestration there gives the user step-by-step progress, useful
``--dry-run`` listings, and a single place to read the contest-apply
flow.

The DOMjudge API does not support contest updates, so when a contest
already exists with different fields the deltas are surfaced via
:class:`ContestApplyResult.skipped_field_changes` rather than applied.
Resource reconciliation (problems, teams) is always idempotent.
"""

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
    support contest updates). The CLI layer renders these to the user.
    """

    contest_shortname: str
    contest_id: str
    skipped_field_changes: list[FieldChange] = field(default_factory=list)


def _team_group_naming(shortname: str) -> tuple[str, str]:
    """Return ``(group_name, group_id)`` for a contest's scoreboard team group."""
    return f"{shortname.upper()} Teams", f"{shortname}-teams"


def _require_shortname(contest: ContestConfig) -> str:
    """Treat shortname as a precondition. Loaders must guarantee it."""
    if contest.shortname is None:
        raise ContestError("Contest configuration is missing required 'shortname'")
    return contest.shortname


class ContestApplicationService:
    """Toolkit for applying contest configurations.

    Each public method corresponds to one step of the contest-apply
    workflow. The operations layer composes these into a named, ordered
    plan; this class never orchestrates them itself.
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
        self.team_service = team_service or TeamService(client, secrets)
        self.state_comparator = state_comparator or ContestStateComparator(client, secrets)

    # ------------------------------------------------------------------ steps

    def compare(self, contest: ContestConfig) -> ContestChangeSet:
        """Compare desired vs. current contest state."""
        shortname = _require_shortname(contest)
        logger.info(
            "Comparing contest state",
            extra={"contest_name": contest.name, "contest_shortname": shortname},
        )
        return self.state_comparator.compare_contest(contest)

    def resolve_or_create(
        self, contest: ContestConfig, change_set: ContestChangeSet
    ) -> tuple[str, list[FieldChange]]:
        """Return ``(contest_id, skipped_field_changes)``.

        Creates a new contest when the change set says so; otherwise
        uses ``change_set.existing_contest_id`` and reports any field
        deltas that cannot be applied via the API.
        """
        shortname = change_set.contest_shortname

        if change_set.change_type == ChangeType.CREATE:
            contest_id = self._create_contest(contest)
            logger.info(f"✓ Created new contest '{shortname}' (ID: {contest_id})")
            return contest_id, []

        if change_set.existing_contest_id is None:
            raise ContestError(
                f"Contest '{shortname}' was expected to exist but no id was resolved"
            )
        contest_id = change_set.existing_contest_id

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

    def provision_team_group(self, contest_id: str, shortname: str) -> str:
        """Create the contest-specific team group used for scoreboard filtering."""
        group_name, group_id = _team_group_naming(shortname)
        result = self.client.groups.create_for_contest(
            contest_id=contest_id, name=group_name, group_id=group_id
        )
        logger.info(f"Created team group '{group_name}' (ID: {result.id}) for contest {shortname}")
        return str(result.id)

    def apply_problems(self, contest: ContestConfig, context: ServiceContext) -> None:
        """Add the contest's problems via :class:`ProblemService`."""
        results = self.problem_service.create_many(contest.problems, context, stop_on_error=False)
        summary = self.problem_service.get_summary(results)
        if summary["failed"] > 0:
            raise ContestError(f"{summary['failed']} problem(s) failed to add")

    def apply_teams(self, contest: ContestConfig, context: ServiceContext) -> None:
        """Add the contest's teams via :class:`TeamService`."""
        results = self.team_service.create_many(contest.teams, context, stop_on_error=False)
        summary = self.team_service.get_summary(results)
        if summary["failed"] > 0:
            raise ContestError(f"{summary['failed']} team(s) failed to add")

    # ------------------------------------------------------------------ helpers

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
