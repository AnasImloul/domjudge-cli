"""Contest state comparison and change detection service."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from dom.core.services.base import StateComparatorService
from dom.domain.team_id_generator import generate_team_username
from dom.logging_config import get_logger
from dom.shared.filesystem import get_secrets_manager
from dom.types.config.processed import ContestConfig

logger = get_logger(__name__)


class ChangeType(str, Enum):
    """Types of changes that can be detected."""

    CREATE = "create"
    UPDATE = "update"
    NO_CHANGE = "no_change"


@dataclass
class FieldChange:
    """Represents a change in a specific field."""

    field: str
    old_value: Any
    new_value: Any

    def __str__(self) -> str:
        """Format change for display."""
        return f"{self.field}: {self.old_value} → {self.new_value}"


@dataclass
class ResourceChange:
    """Represents changes in contest resources (problems/teams)."""

    resource_type: str  # "problems" or "teams"
    to_add: list[str]  # IDs/names to add
    to_remove: list[str]  # IDs/names to remove (not implemented yet)
    unchanged: list[str]  # IDs/names that exist

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.to_add or self.to_remove)

    def __str__(self) -> str:
        """Format resource changes for display."""
        parts = []
        if self.to_add:
            parts.append(f"+{len(self.to_add)} to add")
        if self.to_remove:
            parts.append(f"-{len(self.to_remove)} to remove")
        if self.unchanged:
            parts.append(f"={len(self.unchanged)} unchanged")
        return f"{self.resource_type}: {', '.join(parts) if parts else 'no changes'}"


@dataclass
class ContestChangeSet:
    """Represents all detected changes for a contest."""

    contest_shortname: str
    change_type: ChangeType
    field_changes: list[FieldChange]
    resource_changes: list[ResourceChange]

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes at all."""
        return (
            self.change_type != ChangeType.NO_CHANGE
            or bool(self.field_changes)
            or any(rc.has_changes for rc in self.resource_changes)
        )

    def summary(self) -> str:
        """Get a human-readable summary of changes."""
        if self.change_type == ChangeType.CREATE:
            return f"[green]CREATE[/green] contest '{self.contest_shortname}'"

        if not self.has_changes:
            return f"[dim]NO CHANGES[/dim] for contest '{self.contest_shortname}'"

        parts = []
        if self.field_changes:
            parts.append(f"{len(self.field_changes)} field(s)")
        for rc in self.resource_changes:
            if rc.has_changes:
                parts.append(rc.resource_type)

        return f"[yellow]UPDATE[/yellow] contest '{self.contest_shortname}': {', '.join(parts)}"


class ContestStateComparator(StateComparatorService[ContestConfig, ContestChangeSet]):
    """
    State comparison service for contest configurations.

    Inherits from StateComparatorService to provide a consistent interface
    for state comparison operations across the service layer.

    Architecture Pattern: State Comparison Service
    - Compares desired configuration with current API state
    - Detects field changes, resource additions/removals
    - Returns structured change sets (ContestChangeSet)
    - Enables idempotent operations and safe updates

    This service enables safe live changes by detecting exactly what changed
    between the current state and desired configuration.
    """

    def __init__(self, client):
        """
        Initialize contest state comparator.

        Args:
            client: DOMjudge API client
        """
        self.client = client

    def compare(
        self, desired: ContestConfig, current: dict[str, Any] | None = None
    ) -> ContestChangeSet:
        """
        Compare desired contest configuration with current state.

        Args:
            desired: Desired contest configuration
            current: Current contest state from API (if None, will fetch)

        Returns:
            ContestChangeSet describing all changes
        """
        # shortname is required for state comparison
        assert desired.shortname is not None, "Contest shortname is required for state comparison"

        # Fetch current state if not provided
        if current is None:
            current = self._fetch_current_state(desired.shortname)

        # Determine change type
        if current is None:
            return ContestChangeSet(
                contest_shortname=desired.shortname,
                change_type=ChangeType.CREATE,
                field_changes=[],
                resource_changes=[],
            )

        # Compare fields
        field_changes = self._compare_contest_fields(desired, current)

        # Compare resources (problems and teams)
        contest_id = current["id"]
        problem_changes = self._compare_problems(desired, contest_id)
        team_changes = self._compare_teams(desired, contest_id)

        change_type = ChangeType.UPDATE if field_changes else ChangeType.NO_CHANGE

        return ContestChangeSet(
            contest_shortname=desired.shortname,
            change_type=change_type,
            field_changes=field_changes,
            resource_changes=[problem_changes, team_changes],
        )

    def _fetch_current_state(self, shortname: str) -> dict[str, Any] | None:
        """
        Fetch current contest from API by shortname.

        Args:
            shortname: Contest shortname

        Returns:
            Contest data or None if not found
        """
        try:
            contests = self.client.contests.list_all()
            for contest in contests:
                if contest.get("shortname") == shortname:
                    logger.debug(f"Found existing contest '{shortname}'")
                    return contest  # type: ignore[no-any-return]
            logger.debug(f"Contest '{shortname}' not found (will be created)")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch contest '{shortname}': {e}")
            return None

    def _compare_contest_fields(
        self, desired: ContestConfig, current: dict[str, Any]
    ) -> list[FieldChange]:
        """
        Compare contest fields to detect changes.

        Args:
            desired: Desired configuration
            current: Current state

        Returns:
            List of field changes
        """
        changes = []

        # Map of field names to compare
        fields_to_compare = {
            "name": (desired.name or desired.shortname, current.get("name")),
            "formal_name": (
                desired.formal_name or desired.name,
                current.get("formal_name"),
            ),
            "duration": (desired.duration, current.get("duration")),
            "allow_submit": (desired.allow_submit, current.get("allow_submit")),
            "penalty_time": (desired.penalty_time, current.get("penalty_time")),
        }

        for field, (new_val, old_val) in fields_to_compare.items():
            if new_val is None:
                continue

            # Normalize values for comparison
            if field == "duration":
                # Normalize duration format (handle leading zeros)
                normalized_new = self._normalize_duration(str(new_val))
                normalized_old = self._normalize_duration(str(old_val) if old_val else "")
                if normalized_new != normalized_old:
                    changes.append(FieldChange(field=field, old_value=old_val, new_value=new_val))
                    logger.debug(f"Field change detected: {field} ({old_val} → {new_val})")
            elif str(new_val) != str(old_val):
                changes.append(FieldChange(field=field, old_value=old_val, new_value=new_val))
                logger.debug(f"Field change detected: {field} ({old_val} → {new_val})")

        return changes

    def _normalize_duration(self, duration: str) -> str:
        """
        Normalize duration format for comparison.

        Converts formats like:
        - "5:00:00.000" -> "05:00:00.000"
        - "05:00:00.000" -> "05:00:00.000"
        - "1:30:00" -> "01:30:00.000"

        Args:
            duration: Duration string

        Returns:
            Normalized duration string
        """
        if not duration:
            return ""

        try:
            # Split into time and milliseconds
            if "." in duration:
                time_part, ms_part = duration.split(".")
            else:
                time_part, ms_part = duration, "000"

            # Split time into components
            parts = time_part.split(":")

            if len(parts) == 3:
                hours, minutes, seconds = parts
                # Pad each component to 2 digits
                normalized = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{ms_part}"
                return normalized

            # If format is unexpected, return as-is
            return duration
        except (ValueError, AttributeError):
            # If parsing fails, return as-is
            return duration

    def _compare_problems(self, desired: ContestConfig, contest_id: str) -> ResourceChange:
        """
        Compare problems to detect additions.

        Args:
            desired: Desired configuration
            contest_id: Contest ID

        Returns:
            ResourceChange for problems
        """
        try:
            # Get current problems in contest
            current_problems = self.client.problems.list_for_contest(contest_id)
            current_problem_ids = {p.get("externalid") or p.get("id") for p in current_problems}

            # Get desired problems - ProblemPackage stores externalid in ini.externalid
            desired_problem_ids = {
                p.ini.externalid for p in desired.problems if p.ini and p.ini.externalid
            }

            # Calculate changes
            to_add = list(desired_problem_ids - current_problem_ids)
            unchanged = list(desired_problem_ids & current_problem_ids)

            logger.debug(f"Problem comparison: {len(to_add)} to add, {len(unchanged)} unchanged")

            return ResourceChange(
                resource_type="problems",
                to_add=to_add,
                to_remove=[],  # Not implemented yet
                unchanged=unchanged,
            )
        except Exception as e:
            logger.warning(f"Failed to compare problems: {e}", exc_info=True)
            # On error, assume all need to be added (idempotent operation will handle)
            desired_ids = []
            for p in desired.problems:
                if p.ini and hasattr(p.ini, "externalid") and p.ini.externalid:
                    desired_ids.append(p.ini.externalid)
            return ResourceChange(
                resource_type="problems",
                to_add=desired_ids,
                to_remove=[],
                unchanged=[],
            )

    def _compare_teams(self, desired: ContestConfig, contest_id: str) -> ResourceChange:
        """
        Compare teams to detect additions using deterministic composite names.

        Uses stored seed from secrets manager for deterministic hashing, ensuring
        consistent team IDs across runs. This provides accurate matching using the
        API's composite names as the source of truth.

        Args:
            desired: Desired configuration
            contest_id: Contest ID

        Returns:
            ResourceChange for teams
        """
        try:
            # Get secrets manager for deterministic hashing
            secrets = get_secrets_manager()

            # Get current teams in contest from API (source of truth)
            current_teams = self.client.teams.list_for_contest(contest_id)

            # Build set of composite names from API
            # Format: "team####|name|affiliation|country"
            current_composite_names = {t.get("name") for t in current_teams if t.get("name")}

            # Reconstruct composite names for desired teams using deterministic hashing
            desired_composite_names = {}
            for team in desired.teams:
                # Generate deterministic username (uses stored seed from secrets manager)
                username = generate_team_username(secrets, team.composite_key)

                # Build composite name exactly as it appears in API
                composite_name = f"{username}|{team.composite_key}"

                # Map composite name to display name for user-friendly output
                desired_composite_names[composite_name] = team.name

            # Calculate changes by comparing composite names (exact API match)
            desired_set = set(desired_composite_names.keys())
            to_add_composite = list(desired_set - current_composite_names)
            unchanged_composite = list(desired_set & current_composite_names)

            # Convert to display names for output
            to_add = [desired_composite_names[comp] for comp in to_add_composite]
            unchanged = [desired_composite_names[comp] for comp in unchanged_composite]

            logger.debug(
                f"Team comparison: {len(to_add)} to add, {len(unchanged)} unchanged "
                f"(using deterministic composite names)"
            )

            return ResourceChange(
                resource_type="teams",
                to_add=to_add,
                to_remove=[],
                unchanged=unchanged,
            )
        except Exception as e:
            logger.warning(f"Failed to compare teams: {e}", exc_info=True)
            # On error, assume all need to be added (idempotent operation will handle)
            return ResourceChange(
                resource_type="teams",
                to_add=[t.name for t in desired.teams if t.name],
                to_remove=[],
                unchanged=[],
            )
