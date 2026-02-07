"""CSV preview and analysis utilities for team file import."""

import csv
from pathlib import Path

from rich.console import Console
from rich.table import Table

from dom.logging_config import get_logger

logger = get_logger(__name__)
console = Console()


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
        "id", "name", "team", "affiliation", "organization", "country",
        "university", "college", "school", "institution"
    }
    
    first_row_lower = [cell.lower() for cell in first_row]
    if any(keyword in " ".join(first_row_lower) for keyword in header_keywords):
        return True
    
    return False


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
    has_header: bool | None = None
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
        console.print("[yellow]Warning: CSV file is empty[/yellow]")
        return
    
    # Determine column count
    num_columns = max(len(row) for row in rows) if rows else 0
    
    # Create Rich table
    table = Table(
        title=f"CSV Preview: {file_path.name}",
        caption=f"Showing {len(rows)} of {total_rows} rows",
        show_header=True,
        header_style="bold cyan"
    )
    
    # Add columns based on whether first row is header
    table.add_column("Row", style="dim", width=4)
    
    if has_header and rows:
        # Use first row as column headers
        first_row = rows[0]
        for col_idx, header_name in enumerate(first_row):
            col_label = f"{header_name} (Col {col_idx + 1})" if show_column_numbers else header_name
            table.add_column(col_label, style="green" if col_idx == 0 else "")
        # Pad if necessary
        for col_idx in range(len(first_row), num_columns):
            col_label = f"Col {col_idx + 1}" if show_column_numbers else f"Column {col_idx + 1}"
            table.add_column(col_label)
        
        # Add data rows (skip first row since it's the header)
        for row_idx, row in enumerate(rows[1:], start=2):
            padded_row = row + [""] * (num_columns - len(row))
            table.add_row(str(row_idx), *padded_row)
    else:
        # Use generic column numbers
        if show_column_numbers:
            for col_idx in range(num_columns):
                table.add_column(f"Col {col_idx + 1}", style="green" if col_idx == 0 else "")
        else:
            for col_idx in range(num_columns):
                table.add_column(f"Column {col_idx + 1}")
        
        # Add all rows as data
        for row_idx, row in enumerate(rows, start=1):
            padded_row = row + [""] * (num_columns - len(row))
            table.add_row(str(row_idx), *padded_row)
    
    console.print(table)
    
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


def validate_column_index(column_str: str, num_columns: int) -> int | None:
    """
    Validate and parse a column index from user input.

    Args:
        column_str: User input (e.g., "2" or "$2")
        num_columns: Total number of columns

    Returns:
        Column index (1-indexed) if valid, None otherwise
    """
    # Remove $ prefix if present
    column_str = column_str.strip().lstrip("$")
    
    try:
        col_idx = int(column_str)
        if 1 <= col_idx <= num_columns:
            return col_idx
        else:
            console.print(f"[red]Column {col_idx} is out of range (1-{num_columns})[/red]")
            return None
    except ValueError:
        console.print(f"[red]Invalid column number: {column_str}[/red]")
        return None
