"""CSV preview and analysis utilities for team file import."""

import csv
from collections.abc import Callable
from pathlib import Path

from rich.table import Table

from dom import ui
from dom.logging_config import get_logger
from dom.utils.validators import Invalid

logger = get_logger(__name__)


def read_csv_rows(file_path: Path, delimiter: str, max_rows: int | None = None) -> list[list[str]]:
    """
    Read rows from a CSV file.

    Args:
        file_path: Path to CSV file
        delimiter: Field delimiter
        max_rows: Maximum number of rows to read (None for all)

    Returns:
        List of rows, where each row is a list of strings
    """
    rows = []
    with file_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for idx, row in enumerate(reader):
            if max_rows and idx >= max_rows:
                break
            rows.append([cell.strip() for cell in row])
    return rows


def count_csv_rows(file_path: Path, delimiter: str) -> int:
    """
    Count total number of rows in a CSV file.

    Args:
        file_path: Path to CSV file
        delimiter: Field delimiter

    Returns:
        Total row count
    """
    count = 0
    with file_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for _ in reader:
            count += 1
    return count


def detect_header_row(file_path: Path, delimiter: str) -> bool:
    """
    Auto-detect if the first row appears to be headers.

    Uses heuristics:
    - First row has non-numeric values
    - Subsequent rows have more numeric values
    - First row values look like field names

    Args:
        file_path: Path to CSV file
        delimiter: Field delimiter

    Returns:
        True if first row appears to be headers
    """
    rows = read_csv_rows(file_path, delimiter, max_rows=5)

    if len(rows) < 2:
        return False

    first_row = rows[0]

    # Check if first row has common header keywords
    header_keywords = {
        "id",
        "name",
        "team",
        "affiliation",
        "organization",
        "country",
        "university",
        "college",
        "school",
        "institution",
    }

    first_row_lower = [cell.lower() for cell in first_row]
    return any(keyword in " ".join(first_row_lower) for keyword in header_keywords)


def auto_detect_data_range(file_path: Path, delimiter: str) -> tuple[int, int]:
    """
    Auto-detect the row range containing data (excluding headers).

    Args:
        file_path: Path to CSV file
        delimiter: Field delimiter

    Returns:
        Tuple of (start_row, end_row) - 1-indexed, inclusive
    """
    total_rows = count_csv_rows(file_path, delimiter)
    has_header = detect_header_row(file_path, delimiter)

    start_row = 2 if has_header else 1
    end_row = total_rows

    return start_row, end_row


def preview_csv(
    file_path: Path,
    delimiter: str,
    max_rows: int = 10,
    show_column_numbers: bool = True,
    has_header: bool | None = None,
) -> bool:
    """
    Display a preview of the CSV file with Rich formatting.

    Args:
        file_path: Path to CSV file
        delimiter: Field delimiter
        max_rows: Maximum number of rows to display
        show_column_numbers: Whether to show column numbers
        has_header: Override header detection (None for auto-detect)

    Returns:
        Whether the file has a header row
    """
    rows = read_csv_rows(file_path, delimiter, max_rows=max_rows)
    total_rows = count_csv_rows(file_path, delimiter)
    if has_header is None:
        has_header = detect_header_row(file_path, delimiter)

    if not rows:
        ui.warn("Warning: CSV file is empty")
        return False

    num_columns = max(len(row) for row in rows)

    table = Table(
        title=f"CSV Preview: {file_path.name}",
        caption=f"Showing {len(rows)} of {total_rows} rows",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Row", style="dim", width=4)

    header_row = rows[0] if has_header else []
    data_rows = rows[1:] if has_header else rows
    start_index = 2 if has_header else 1

    for col_idx in range(num_columns):
        if col_idx < len(header_row):
            base = header_row[col_idx]
            label = f"{base} (Col {col_idx + 1})" if show_column_numbers else base
        else:
            label = f"Col {col_idx + 1}" if show_column_numbers else f"Column {col_idx + 1}"
        table.add_column(label, style="green" if col_idx == 0 else "")

    for offset, row in enumerate(data_rows):
        padded = row + [""] * (num_columns - len(row))
        table.add_row(str(start_index + offset), *padded)

    ui.render(table)
    return has_header


def get_column_count(file_path: Path, delimiter: str) -> int:
    """
    Get the number of columns in the CSV file.

    Args:
        file_path: Path to CSV file
        delimiter: Field delimiter

    Returns:
        Number of columns
    """
    rows = read_csv_rows(file_path, delimiter, max_rows=5)
    if not rows:
        return 0
    return max(len(row) for row in rows)


def column_index_parser(num_columns: int, *, optional: bool = False) -> Callable[[str], int | None]:
    """Build a parser for a 1-indexed CSV column number.

    Suitable for ``ui.ask(parser=...)``. Accepts ``"2"`` or ``"$2"`` style.
    When ``optional=True``, an empty input parses to ``None``; otherwise
    empty input raises :class:`Invalid` so ``ui.ask`` reprompts.
    """

    def parse(value: str) -> int | None:
        stripped = value.strip().lstrip("$")
        if not stripped:
            if optional:
                return None
            raise Invalid("This field cannot be empty.")
        try:
            col = int(stripped)
        except ValueError as e:
            raise Invalid(f"Invalid column number: {stripped}") from e
        if not 1 <= col <= num_columns:
            raise Invalid(f"Column {col} is out of range (1-{num_columns}).")
        return col

    return parse
