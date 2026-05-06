"""Tests for time formatting helpers in dom.utils.time."""

from dom.utils.time import format_datetime, format_duration


class TestFormatDatetime:
    """Tests for format_datetime."""

    def test_converts_space_separated_to_iso8601_utc(self):
        """A 'YYYY-MM-DD HH:MM:SS' string is reformatted with the +00:00 offset."""
        assert format_datetime("2026-05-06 14:30:00") == "2026-05-06T14:30:00+00:00"

    def test_returns_input_unchanged_when_format_does_not_match(self):
        """Strings that don't match the expected format pass through untouched."""
        assert format_datetime("not a date") == "not a date"
        assert format_datetime("2026-05-06T14:30:00Z") == "2026-05-06T14:30:00Z"


class TestFormatDuration:
    """Tests for format_duration."""

    def test_appends_milliseconds_when_missing(self):
        """A 'HH:MM:SS' string gets '.000' appended."""
        assert format_duration("05:00:00") == "05:00:00.000"

    def test_leaves_string_unchanged_when_milliseconds_present(self):
        """If milliseconds are already present (any amount), pass through."""
        assert format_duration("05:00:00.123") == "05:00:00.123"
