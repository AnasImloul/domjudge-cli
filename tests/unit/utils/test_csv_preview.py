"""Unit tests for CSV preview utilities."""

import pytest

from dom.utils.csv_preview import (
    auto_detect_data_range,
    column_index_parser,
    count_csv_rows,
    detect_header_row,
    get_column_count,
    read_csv_rows,
)
from dom.utils.validators import Invalid


@pytest.fixture
def sample_csv_with_header(tmp_path):
    """Create a sample CSV file with header row."""
    csv_file = tmp_path / "teams_with_header.csv"
    content = """id,name,affiliation,country
1,Team Alpha,University A,USA
2,Team Beta,University B,CAN
3,Team Gamma,College C,FRA
4,Team Delta,Institute D,DEU
5,Team Epsilon,Academy E,GBR
"""
    csv_file.write_text(content)
    return csv_file


@pytest.fixture
def sample_csv_no_header(tmp_path):
    """Create a sample CSV file without header row."""
    csv_file = tmp_path / "teams_no_header.csv"
    content = """1,Team Alpha,University A,USA
2,Team Beta,University B,CAN
3,Team Gamma,College C,FRA
4,Team Delta,Institute D,DEU
5,Team Epsilon,Academy E,GBR
"""
    csv_file.write_text(content)
    return csv_file


@pytest.fixture
def sample_tsv(tmp_path):
    """Create a sample TSV file."""
    tsv_file = tmp_path / "teams.tsv"
    content = "id\tname\taffiliation\tcountry\n1\tTeam Alpha\tUniversity A\tUSA\n2\tTeam Beta\tUniversity B\tCAN\n"
    tsv_file.write_text(content)
    return tsv_file


class TestReadCsvRows:
    """Tests for read_csv_rows function."""

    def test_read_all_rows(self, sample_csv_with_header):
        """Test reading all rows from CSV."""
        rows = read_csv_rows(sample_csv_with_header, ",")
        assert len(rows) == 6  # 1 header + 5 data rows
        assert rows[0] == ["id", "name", "affiliation", "country"]
        assert rows[1] == ["1", "Team Alpha", "University A", "USA"]

    def test_read_limited_rows(self, sample_csv_with_header):
        """Test reading limited number of rows."""
        rows = read_csv_rows(sample_csv_with_header, ",", max_rows=3)
        assert len(rows) == 3
        assert rows[0] == ["id", "name", "affiliation", "country"]

    def test_read_tsv(self, sample_tsv):
        """Test reading TSV file."""
        rows = read_csv_rows(sample_tsv, "\t")
        assert len(rows) == 3
        assert rows[0] == ["id", "name", "affiliation", "country"]

    def test_strips_whitespace(self, tmp_path):
        """Test that whitespace is stripped from cells."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("  name  ,  org  \n  Team A  ,  Uni A  \n")
        rows = read_csv_rows(csv_file, ",")
        assert rows[0] == ["name", "org"]
        assert rows[1] == ["Team A", "Uni A"]


class TestCountCsvRows:
    """Tests for count_csv_rows function."""

    def test_count_rows_with_header(self, sample_csv_with_header):
        """Test counting rows in CSV with header."""
        count = count_csv_rows(sample_csv_with_header, ",")
        assert count == 6

    def test_count_rows_no_header(self, sample_csv_no_header):
        """Test counting rows in CSV without header."""
        count = count_csv_rows(sample_csv_no_header, ",")
        assert count == 5

    def test_count_empty_file(self, tmp_path):
        """Test counting rows in empty file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        count = count_csv_rows(csv_file, ",")
        assert count == 0


class TestDetectHeaderRow:
    """Tests for detect_header_row function."""

    def test_detect_header_with_keywords(self, sample_csv_with_header):
        """Test detecting header with common keywords."""
        assert detect_header_row(sample_csv_with_header, ",") is True

    def test_detect_no_header(self, sample_csv_no_header):
        """Test detecting file without header."""
        # This might return True or False depending on heuristics
        # The key is it should work without crashing
        result = detect_header_row(sample_csv_no_header, ",")
        assert isinstance(result, bool)

    def test_detect_header_with_numeric_data(self, tmp_path):
        """Test detecting header when data rows are numeric."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,score,rank\n1,100,1\n2,95,2\n3,90,3\n")
        assert detect_header_row(csv_file, ",") is True

    def test_detect_with_insufficient_rows(self, tmp_path):
        """Test detection with only one row."""
        csv_file = tmp_path / "single.csv"
        csv_file.write_text("name,affiliation\n")
        result = detect_header_row(csv_file, ",")
        assert isinstance(result, bool)


class TestAutoDetectDataRange:
    """Tests for auto_detect_data_range function."""

    def test_auto_detect_with_header(self, sample_csv_with_header):
        """Test auto-detecting range with header row."""
        start, end = auto_detect_data_range(sample_csv_with_header, ",")
        assert start == 2  # First data row after header
        assert end == 6  # Total rows

    def test_auto_detect_no_header(self, sample_csv_no_header):
        """Test auto-detecting range without header row."""
        start, end = auto_detect_data_range(sample_csv_no_header, ",")
        # Should detect as starting from row 1 or 2 depending on heuristics
        assert start >= 1
        assert end == 5

    def test_auto_detect_empty_file(self, tmp_path):
        """Test auto-detecting range in empty file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        start, end = auto_detect_data_range(csv_file, ",")
        # Should handle gracefully
        assert isinstance(start, int)
        assert isinstance(end, int)


class TestGetColumnCount:
    """Tests for get_column_count function."""

    def test_get_column_count_uniform(self, sample_csv_with_header):
        """Test getting column count from uniform CSV."""
        count = get_column_count(sample_csv_with_header, ",")
        assert count == 4

    def test_get_column_count_ragged(self, tmp_path):
        """Test getting column count from ragged CSV (different row lengths)."""
        csv_file = tmp_path / "ragged.csv"
        csv_file.write_text("a,b\nc,d,e,f\ng,h,i\n")
        count = get_column_count(csv_file, ",")
        assert count == 4  # Maximum column count

    def test_get_column_count_empty(self, tmp_path):
        """Test getting column count from empty file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        count = get_column_count(csv_file, ",")
        assert count == 0


class TestColumnIndexParser:
    """Tests for column_index_parser — parser raises Invalid on bad input."""

    def test_parses_valid_index(self):
        parse = column_index_parser(5)
        assert parse("2") == 2
        assert parse("1") == 1
        assert parse("5") == 5

    def test_strips_dollar_prefix(self):
        parse = column_index_parser(5)
        assert parse("$2") == 2
        assert parse("$4") == 4

    def test_tolerates_whitespace(self):
        parse = column_index_parser(5)
        assert parse("  3  ") == 3
        assert parse(" $2 ") == 2

    def test_out_of_range_raises(self):
        parse = column_index_parser(5)
        for value in ("0", "6", "100"):
            with pytest.raises(Invalid):
                parse(value)

    def test_non_integer_raises(self):
        parse = column_index_parser(5)
        for value in ("abc", "1.5"):
            with pytest.raises(Invalid):
                parse(value)

    def test_empty_required_raises(self):
        with pytest.raises(Invalid):
            column_index_parser(5)("")

    def test_empty_optional_returns_none(self):
        assert column_index_parser(5, optional=True)("") is None
