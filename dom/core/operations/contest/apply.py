"""Apply contest configuration to the DOMjudge platform.

The operation expands each contest in the configuration into a fixed
five-step workflow (compare → resolve-or-create → provision team
group → apply problems → apply teams). Steps mutate a per-contest
:class:`_ContestSession` via closures; the aggregate
:class:`ContestApplyResult` list is built from those sessions and
returned so the CLI can render any field-change warnings.
"""

from dataclasses import dataclass, field

from dom.core.operations.framework import Context, Step, Steps, operation
from dom.core.operations.wiring import wire_admin_api
from dom.core.services.base import ServiceContext
from dom.core.services.contest.apply import ContestApplicationService, ContestApplyResult
from dom.core.services.contest.changes import ContestChangeSet, FieldChange
from dom.core.services.problem.apply import ProblemService
from dom.core.services.team.apply import TeamService
from dom.types.config.processed import ContestConfig, DomConfig


@dataclass
class _ContestSession:
    """Per-contest state threaded across this contest's Steps via closures."""

    config: ContestConfig
    change_set: ContestChangeSet | None = None
    contest_id: str | None = None
    team_group_id: str | None = None
    skipped_field_changes: list[FieldChange] = field(default_factory=list)

    @property
    def shortname(self) -> str:
        return self.config.shortname or "?"

    def to_result(self) -> ContestApplyResult:
        return ContestApplyResult(
            contest_shortname=self.shortname,
            contest_id=self.contest_id or "",
            skipped_field_changes=self.skipped_field_changes,
        )


def _summary(results: list[ContestApplyResult]) -> str:
    if len(results) == 1:
        r = results[0]
        suffix = " (with skipped field changes)" if r.skipped_field_changes else ""
        return f"Applied '{r.contest_shortname}'{suffix}"
    skipped = sum(1 for r in results if r.skipped_field_changes)
    suffix = f" • {skipped} with skipped field changes" if skipped else ""
    return f"Applied {len(results)} contests{suffix}"


def _build_contest_steps(svc: ContestApplicationService, session: _ContestSession) -> list[Step]:
    """Five named steps that together apply one contest."""
    sn = session.shortname

    def context() -> ServiceContext:
        return ServiceContext(
            client=svc.client,
            contest_id=session.contest_id,
            contest_shortname=sn,
            team_group_id=session.team_group_id,
        )

    def compare_step() -> None:
        session.change_set = svc.compare(session.config)

    def resolve_step() -> None:
        assert session.change_set is not None
        contest_id, skipped = svc.resolve_or_create(session.config, session.change_set)
        session.contest_id = contest_id
        session.skipped_field_changes = skipped

    def provision_step() -> None:
        assert session.contest_id is not None
        session.team_group_id = svc.provision_team_group(session.contest_id, sn)

    def apply_problems_step() -> None:
        svc.apply_problems(session.config, context())

    def apply_teams_step() -> None:
        svc.apply_teams(session.config, context())

    return [
        Step(f"[{sn}] Compare state", compare_step),
        Step(f"[{sn}] Create or resolve", resolve_step),
        Step(f"[{sn}] Provision team group", provision_step),
        Step(f"[{sn}] Apply problems", apply_problems_step),
        Step(f"[{sn}] Apply teams", apply_teams_step),
    ]


@operation("Apply contests", summary=_summary)
def apply_contests_op(ctx: Context, config: DomConfig) -> Steps:
    if not config.contests:
        raise ValueError("No contests in configuration")

    client = wire_admin_api(config.infra, ctx.secrets)
    svc = ContestApplicationService(
        client,
        ctx.secrets,
        problem_service=ProblemService(client),
        team_service=TeamService(client, ctx.secrets),
    )

    sessions = [_ContestSession(config=c) for c in config.contests]
    steps: list[Step] = []
    for session in sessions:
        steps.extend(_build_contest_steps(svc, session))

    return Steps(steps=steps, result=lambda: [s.to_result() for s in sessions])
