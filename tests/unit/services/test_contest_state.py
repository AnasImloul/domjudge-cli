"""Tests for contest state comparison and change detection."""

from unittest.mock import MagicMock

import pytest

from dom.core.services.contest.state import (
    ChangeType,
    ContestChangeSet,
    ContestStateComparator,
    FieldChange,
    ResourceChange,
)
from dom.types.config.processed import ContestConfig


class TestContestStateComparator:
    """Tests for ContestStateComparator."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DomJudge API client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def comparator(self, mock_client):
        """Create a ContestStateComparator with mocked client."""
        return ContestStateComparator(mock_client)

    def test_compare_contest_detects_new_contest(self, comparator, mock_client):
        """Test that CREATE is detected for new contests."""
        desired = ContestConfig(
            name="Test Contest", shortname="test2025", duration="5:00:00", problems=[], teams=[]
        )

        # Mock: contest doesn't exist
        mock_client.contests.list_all.return_value = []

        result = comparator.compare_contest(desired)

        assert result.change_type == ChangeType.CREATE
        assert result.contest_shortname == "test2025"
        assert len(result.field_changes) == 0
        assert len(result.resource_changes) == 0

    def test_compare_contest_detects_no_changes(self, comparator, mock_client):
        """Test that NO_CHANGE is detected when contest matches."""
        desired = ContestConfig(
            name="Test Contest",
            shortname="test2025",
            formal_name="Test Contest",  # Must match name if not provided
            start_time=None,
            duration="5:00:00",
            penalty_time=0,
            allow_submit=True,
            problems=[],
            teams=[],
        )

        # Mock: contest exists with same values
        # Note: formal_name in API matches the fallback logic (formal_name or name)
        mock_client.contests.list_all.return_value = [
            {
                "id": "1",
                "shortname": "test2025",
                "name": "Test Contest",
                "formal_name": "Test Contest",
                "duration": "5:00:00",
                "allow_submit": True,
                "penalty_time": 0,
            }
        ]
        mock_client.problems.list_for_contest.return_value = []
        mock_client.teams.list_for_contest.return_value = []

        result = comparator.compare_contest(desired)

        assert result.change_type == ChangeType.NO_CHANGE
        assert len(result.field_changes) == 0

    def test_compare_contest_detects_field_changes(self, comparator, mock_client):
        """Test that field changes are detected."""
        desired = ContestConfig(
            name="Test Contest",
            shortname="test2025",
            formal_name="Test Contest",
            start_time=None,
            duration="6:00:00",  # Changed from 5:00:00
            penalty_time=0,
            allow_submit=True,
            problems=[],
            teams=[],
        )

        # Mock: contest exists with different duration
        mock_client.contests.list_all.return_value = [
            {
                "id": "1",
                "shortname": "test2025",
                "name": "Test Contest",
                "formal_name": "Test Contest",
                "duration": "5:00:00",
                "allow_submit": True,
                "penalty_time": 0,
            }
        ]
        mock_client.problems.list_for_contest.return_value = []
        mock_client.teams.list_for_contest.return_value = []

        result = comparator.compare_contest(desired)

        assert result.change_type == ChangeType.UPDATE
        assert len(result.field_changes) == 1
        assert result.field_changes[0].field == "duration"
        assert result.field_changes[0].old_value == "5:00:00"
        assert result.field_changes[0].new_value == "6:00:00"

    def test_fetch_current_contest_finds_existing(self, comparator, mock_client):
        """Test that existing contest is found by shortname."""
        mock_client.contests.list_all.return_value = [
            {"id": "1", "shortname": "test2025", "name": "Test"},
            {"id": "2", "shortname": "other", "name": "Other"},
        ]

        result = comparator._fetch_current_contest("test2025")

        assert result is not None
        assert result["shortname"] == "test2025"
        assert result["id"] == "1"

    def test_fetch_current_contest_returns_none_when_not_found(self, comparator, mock_client):
        """Test that None is returned when contest doesn't exist."""
        mock_client.contests.list_all.return_value = [
            {"id": "1", "shortname": "other", "name": "Other"}
        ]

        result = comparator._fetch_current_contest("test2025")

        assert result is None

    def test_fetch_current_contest_handles_api_errors(self, comparator, mock_client):
        """Test that API errors are handled gracefully."""
        mock_client.contests.list_all.side_effect = Exception("API Error")

        result = comparator._fetch_current_contest("test2025")

        assert result is None


class TestFieldChange:
    """Tests for FieldChange dataclass."""

    def test_field_change_string_representation(self):
        """Test that FieldChange has readable string representation."""
        change = FieldChange(field="duration", old_value="5:00:00", new_value="6:00:00")

        str_repr = str(change)
        assert "duration" in str_repr
        assert "5:00:00" in str_repr
        assert "6:00:00" in str_repr


class TestResourceChange:
    """Tests for ResourceChange dataclass."""

    def test_resource_change_detects_additions(self):
        """Test that additions are detected."""
        change = ResourceChange(
            resource_type="problems", to_add=["problem-a", "problem-b"], to_remove=[], unchanged=[]
        )

        assert change.has_changes is True
        assert len(change.to_add) == 2

    def test_resource_change_detects_no_changes(self):
        """Test that no changes is detected correctly."""
        change = ResourceChange(
            resource_type="problems", to_add=[], to_remove=[], unchanged=["problem-a"]
        )

        assert change.has_changes is False

    def test_resource_change_string_representation(self):
        """Test that ResourceChange has readable string representation."""
        change = ResourceChange(
            resource_type="teams", to_add=["Team A", "Team B"], to_remove=[], unchanged=[]
        )

        str_repr = str(change)
        assert "teams" in str_repr
        assert "2" in str_repr


class TestContestChangeSet:
    """Tests for ContestChangeSet dataclass."""

    def test_change_set_summary_for_create(self):
        """Test summary message for CREATE."""
        change_set = ContestChangeSet(
            contest_shortname="test2025",
            change_type=ChangeType.CREATE,
            field_changes=[],
            resource_changes=[],
        )

        summary = change_set.summary()
        assert "CREATE" in summary
        assert "test2025" in summary

    def test_change_set_summary_for_update(self):
        """Test summary message for UPDATE."""
        field_changes = [FieldChange("duration", "5:00:00", "6:00:00")]
        resource_changes = [ResourceChange("problems", ["problem-a"], [], [])]

        change_set = ContestChangeSet(
            contest_shortname="test2025",
            change_type=ChangeType.UPDATE,
            field_changes=field_changes,
            resource_changes=resource_changes,
        )

        summary = change_set.summary()
        assert "UPDATE" in summary
        assert "test2025" in summary

    def test_change_set_summary_for_no_change(self):
        """Test summary message for NO_CHANGE."""
        change_set = ContestChangeSet(
            contest_shortname="test2025",
            change_type=ChangeType.NO_CHANGE,
            field_changes=[],
            resource_changes=[],
        )

        summary = change_set.summary()
        assert "NO CHANGES" in summary
        assert "test2025" in summary

    def test_change_set_with_multiple_field_changes(self):
        """Test that multiple field changes are tracked."""
        field_changes = [
            FieldChange("duration", "5:00:00", "6:00:00"),
            FieldChange("name", "Old Name", "New Name"),
        ]

        change_set = ContestChangeSet(
            contest_shortname="test2025",
            change_type=ChangeType.UPDATE,
            field_changes=field_changes,
            resource_changes=[],
        )

        assert len(change_set.field_changes) == 2
        assert change_set.change_type == ChangeType.UPDATE

    def test_change_set_with_multiple_resource_changes(self):
        """Test that multiple resource types are tracked."""
        resource_changes = [
            ResourceChange("problems", ["problem-a"], [], []),
            ResourceChange("teams", ["Team A"], [], []),
        ]

        change_set = ContestChangeSet(
            contest_shortname="test2025",
            change_type=ChangeType.UPDATE,
            field_changes=[],
            resource_changes=resource_changes,
        )

        assert len(change_set.resource_changes) == 2
