"""Contest state comparison and change detection service.

The comparator is structured around three declarative pieces:

* :data:`_FIELD_SPECS` — the list of contest fields to diff, each with
  its own value extractors and (optional) normalizer.
* :func:`_diff_resource` — a generic "compare desired vs current by key"
  helper used for problems and teams.
* :class:`ContestStateComparator` — wires the API client into the above.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from dom.core.services.contest.changes import (
    ChangeType,
    ContestChangeSet,
    FieldChange,
    ResourceChange,
)
from dom.core.services.protocols import DomJudgeAPIProtocol
from dom.exceptions import APIError, ContestError
from dom.logging_config import get_logger
from dom.types.config.processed import ContestConfig
from dom.utils.cli import get_secrets_manager
from dom.utils.hashing import generate_team_username

logger = get_logger(__name__)

# ---------------------------------------------------------------- field specs


@dataclass(frozen=True)
class _FieldSpec:
    """How to read and compare one contest field."""

    name: str
    extract_desired: Callable[[ContestConfig], Any]
    extract_current: Callable[[dict[str, Any]], Any]
    normalize: Callable[[Any], Any] = lambda v: None if v is None else str(v)


def _normalize_duration(value: Any) -> str:
    """Pad ``H:MM:SS[.ms]`` to ``HH:MM:SS.mmm`` so format variations compare equal."""
    if not value:
        return ""
    duration = str(value)
    try:
        time_part, ms_part = duration.split(".") if "." in duration else (duration, "000")
        parts = time_part.split(":")
        if len(parts) != 3:
            return duration
        h, m, s = parts
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{ms_part}"
    except (ValueError, AttributeError):
        return duration


_FIELD_SPECS: tuple[_FieldSpec, ...] = (
    _FieldSpec(
        name="name",
        extract_desired=lambda d: d.name or d.shortname,
        extract_current=lambda c: c.get("name"),
    ),
    _FieldSpec(
        name="formal_name",
        extract_desired=lambda d: d.formal_name or d.name,
        extract_current=lambda c: c.get("formal_name"),
    ),
    _FieldSpec(
        name="duration",
        extract_desired=lambda d: d.duration,
        extract_current=lambda c: c.get("duration"),
        normalize=_normalize_duration,
    ),
    _FieldSpec(
        name="allow_submit",
        extract_desired=lambda d: d.allow_submit,
        extract_current=lambda c: c.get("allow_submit"),
    ),
    _FieldSpec(
        name="penalty_time",
        extract_desired=lambda d: d.penalty_time,
        extract_current=lambda c: c.get("penalty_time"),
    ),
)


# ---------------------------------------------------------------- generic diff


@dataclass(frozen=True)
class _Diff:
    to_add: list[str]
    unchanged: list[str]


def _diff_resource(
    desired_keys: Iterable[str],
    current_keys: Iterable[str],
    *,
    display: dict[str, str] | None = None,
) -> _Diff:
    """Set-diff two key collections, optionally projecting back to display names."""
    desired_set = set(desired_keys)
    current_set = set(current_keys)
    project = (lambda k: display[k]) if display else (lambda k: k)
    return _Diff(
        to_add=[project(k) for k in desired_set - current_set],
        unchanged=[project(k) for k in desired_set & current_set],
    )


# ---------------------------------------------------------------- comparator


class ContestStateComparator:
    """Compare desired contest state with the live state from the API.

    Used by both ``plan`` (to preview changes) and ``apply`` (to decide
    create-vs-skip per contest).
    """

    def __init__(self, client: DomJudgeAPIProtocol):
        self.client = client

    def compare_contest(
        self, desired: ContestConfig, current: dict[str, Any] | None = None
    ) -> ContestChangeSet:
        shortname = _require_shortname(desired)
        if current is None:
            current = self._fetch_current_contest(shortname)

        if current is None:
            return ContestChangeSet(
                contest_shortname=shortname,
                change_type=ChangeType.CREATE,
                field_changes=[],
                resource_changes=[],
            )

        field_changes = self._diff_fields(desired, current)
        contest_id = current["id"]
        return ContestChangeSet(
            contest_shortname=shortname,
            change_type=ChangeType.UPDATE if field_changes else ChangeType.NO_CHANGE,
            field_changes=field_changes,
            resource_changes=[
                self._diff_problems(desired, contest_id),
                self._diff_teams(desired, contest_id),
            ],
        )

    # ------------------------------------------------------------------ fetch

    def _fetch_current_contest(self, shortname: str) -> dict[str, Any] | None:
        try:
            for contest in self.client.contests.list_all():
                if contest.get("shortname") == shortname:
                    logger.debug(f"Found existing contest '{shortname}'")
                    return contest
        except APIError as e:
            logger.warning(f"Failed to fetch contest '{shortname}': {e}")
            return None
        logger.debug(f"Contest '{shortname}' not found (will be created)")
        return None

    # ------------------------------------------------------------------ fields

    def _diff_fields(self, desired: ContestConfig, current: dict[str, Any]) -> list[FieldChange]:
        """Walk the field specs and emit a FieldChange per detected delta."""
        changes: list[FieldChange] = []
        for spec in _FIELD_SPECS:
            new_val = spec.extract_desired(desired)
            if new_val is None:
                continue
            old_val = spec.extract_current(current)
            if spec.normalize(new_val) != spec.normalize(old_val):
                logger.debug(f"Field change detected: {spec.name} ({old_val} → {new_val})")
                changes.append(FieldChange(field=spec.name, old_value=old_val, new_value=new_val))
        return changes

    # ------------------------------------------------------------------ resources

    def _diff_problems(self, desired: ContestConfig, contest_id: str) -> ResourceChange:
        desired_ids = [p.ini.externalid for p in desired.problems if p.ini and p.ini.externalid]
        try:
            current = self.client.problems.list_for_contest(contest_id)
        except APIError as e:
            logger.warning(f"Failed to compare problems: {e}", exc_info=True)
            # Fall back to assuming everything is new; the apply path is idempotent.
            return ResourceChange(
                resource_type="problems", to_add=desired_ids, to_remove=[], unchanged=[]
            )

        current_ids = [str(p.get("externalid") or p.get("id")) for p in current]
        diff = _diff_resource(desired_ids, current_ids)
        logger.debug(
            f"Problem comparison: {len(diff.to_add)} to add, {len(diff.unchanged)} unchanged"
        )
        return ResourceChange(
            resource_type="problems",
            to_add=diff.to_add,
            to_remove=[],
            unchanged=diff.unchanged,
        )

    def _diff_teams(self, desired: ContestConfig, contest_id: str) -> ResourceChange:
        """Compare teams using deterministic composite names as the join key.

        DOMjudge stores team names as ``"team####|name|affiliation|country"``.
        We reconstruct that exact form for desired teams (using the stored
        seed for stable hashing) so the comparison is an exact string match.
        Display names are projected back through the ``key → name`` map.
        """
        secrets = get_secrets_manager()
        composite_to_display: dict[str, str] = {
            f"{generate_team_username(secrets, t.composite_key)}|{t.composite_key}": t.name
            for t in desired.teams
        }

        try:
            current = self.client.teams.list_for_contest(contest_id)
        except APIError as e:
            logger.warning(f"Failed to compare teams: {e}", exc_info=True)
            return ResourceChange(
                resource_type="teams",
                to_add=[t.name for t in desired.teams if t.name],
                to_remove=[],
                unchanged=[],
            )

        current_keys = [str(name) for t in current if (name := t.get("name"))]
        diff = _diff_resource(
            composite_to_display.keys(), current_keys, display=composite_to_display
        )
        logger.debug(
            f"Team comparison: {len(diff.to_add)} to add, {len(diff.unchanged)} unchanged "
            "(using deterministic composite names)"
        )
        return ResourceChange(
            resource_type="teams",
            to_add=diff.to_add,
            to_remove=[],
            unchanged=diff.unchanged,
        )


# ---------------------------------------------------------------- helpers


def _require_shortname(contest: ContestConfig) -> str:
    if contest.shortname is None:
        raise ContestError("Contest configuration is missing required 'shortname'")
    return contest.shortname
