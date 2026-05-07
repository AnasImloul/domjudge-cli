"""Data types describing detected contest changes.

Kept separate from the comparator service so callers can consume the change
shapes without depending on the comparison logic.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


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

    def summary_parts(self) -> tuple[ChangeType, str, list[str]]:
        """Return the raw pieces a renderer needs.

        Returns a ``(change_type, contest_shortname, parts)`` triple
        where ``parts`` describes what's changing — empty when there
        are no changes. Presentation (markup, prefixes) is the caller's
        responsibility.
        """
        if self.change_type == ChangeType.CREATE or not self.has_changes:
            return self.change_type, self.contest_shortname, []

        parts: list[str] = []
        if self.field_changes:
            parts.append(f"{len(self.field_changes)} field(s)")
        for rc in self.resource_changes:
            if rc.has_changes:
                parts.append(rc.resource_type)
        return self.change_type, self.contest_shortname, parts
