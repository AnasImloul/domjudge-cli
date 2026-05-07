import datetime as dt
from pathlib import Path

from rich.console import Console
from rich.table import Table

from dom.templates.init import contest_template
from dom.utils.csv_preview import (
    count_csv_rows,
    get_column_count,
    preview_csv,
    validate_column_index,
)
from dom.utils.prompt import ask, ask_bool
from dom.utils.time import format_datetime, format_duration
from dom.utils.validators import ValidatorBuilder

console = Console()


def initialize_contest():
    console.print("\n[bold cyan]Contest Configuration[/bold cyan]")
    console.print("Set up the parameters for your coding contest")

    name = ask(
        "Contest name",
        console=console,
        parser=ValidatorBuilder.string(none_as_empty=True).strip().non_empty().build(),
    )
    shortname = ask(
        "Contest shortname",
        console=console,
        parser=ValidatorBuilder.string(none_as_empty=True).strip().non_empty().build(),
    )

    default_start = (dt.datetime.now() + dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    start_dt = ask(
        "Start time (YYYY-MM-DD HH:MM:SS)",
        console=console,
        default=default_start,
        parser=ValidatorBuilder.datetime("%Y-%m-%d %H:%M:%S").build(),
    )

    h, m, s = ask(
        "Duration (HH:MM:SS)",
        console=console,
        default="05:00:00",
        parser=ValidatorBuilder.duration_hms().build(),
    )
    duration_str = f"{h:02d}:{m:02d}:{s:02d}"

    penalty_minutes = ask(
        "Penalty time (minutes)",
        console=console,
        default="20",
        parser=ValidatorBuilder.integer().positive().build(),
    )

    allow_submit = ask_bool("Allow submissions?", console=console, default=True)

    teams_path = ask(
        "Teams file path (CSV/TSV)",
        console=console,
        default="teams.csv",
        parser=ValidatorBuilder.path()
        .must_exist()
        .must_be_file()
        .allowed_extensions(["csv", "tsv"])
        .build(),
    )
    suggested_delim = "," if teams_path.endswith(".csv") else "\t"

    delimiter_aliases = {
        ",": ",",
        ";": ";",
        "\t": "\t",
        "comma": ",",
        "semicolon": ";",
        "tab": "\t",
    }
    delimiter = ask(
        f"Field delimiter (Enter for default: {suggested_delim!r})",
        console=console,
        default=suggested_delim,
        parser=ValidatorBuilder.string()
        .one_of(delimiter_aliases)
        .map(delimiter_aliases.__getitem__)
        .build(),
        show_default=False,
    )

    # Show CSV preview
    console.print("\n[bold cyan]CSV Preview[/bold cyan]")
    teams_file_path = Path(teams_path)

    # Initial preview with auto-detection
    has_header = preview_csv(teams_file_path, delimiter, max_rows=10, show_column_numbers=True)

    # Confirm header detection; re-render preview only if the user disagrees.
    confirmed = ask_bool("Does the first row contain headers?", console=console, default=has_header)
    if confirmed != has_header:
        has_header = confirmed
        label = "with header" if has_header else "no header"
        console.print(f"\n[bold cyan]Updated CSV Preview ({label})[/bold cyan]")
        preview_csv(
            teams_file_path,
            delimiter,
            max_rows=10,
            show_column_numbers=True,
            has_header=has_header,
        )

    # Get column count for validation
    num_columns = get_column_count(teams_file_path, delimiter)

    # Interactive column mapping
    console.print("\n[bold cyan]Column Mapping[/bold cyan]")
    console.print(
        "Specify which columns contain team information (use column numbers from preview)"
    )

    def ask_column(prompt: str, default: str, *, optional: bool = False) -> int | None:
        builder = ValidatorBuilder.string().strip()
        if not optional:
            builder = builder.non_empty()
        parser = builder.build()
        while True:
            raw = ask(prompt, console=console, default=default, parser=parser)
            if optional and not raw:
                return None
            col = validate_column_index(raw, num_columns)
            if col is not None:
                return col

    name_column = ask_column("Name column", "1")
    affiliation_column = ask_column("Affiliation column", "2")
    country_column = ask_column("Country column (optional, press Enter to skip)", "", optional=True)

    # Auto-detect row range based on confirmed header status
    total_rows = count_csv_rows(teams_file_path, delimiter)
    start_row = 2 if has_header else 1
    end_row = total_rows
    detected_teams_count = end_row - start_row + 1

    console.print(
        f"\n[bold green]Detected {detected_teams_count} teams in rows {start_row}-{end_row}[/bold green]"
    )
    rows_confirmed = ask_bool(
        "Is this row range correct?",
        console=console,
        default=True,
    )

    if not rows_confirmed:
        console.print("Please specify the correct row range:")
        positive_int = ValidatorBuilder.integer().positive().build()
        start_row = ask(
            "Start row (1-indexed)", console=console, default=str(start_row), parser=positive_int
        )
        end_row = ask(
            "End row (1-indexed)", console=console, default=str(end_row), parser=positive_int
        )

    rows = f"{start_row}-{end_row}"

    # Summary
    table = Table(title="Contest Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Name", name)
    table.add_row("Shortname", shortname)
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    table.add_row("Start time", start_str)
    table.add_row("Duration", duration_str)
    table.add_row("Penalty time", f"{penalty_minutes} minutes")
    table.add_row("Allow submit", "Yes" if allow_submit else "No")
    table.add_row("Teams file", teams_path)
    table.add_row("Teams row range", rows)
    table.add_row("Name column", f"{name_column}")
    table.add_row("Affiliation column", f"{affiliation_column}")
    table.add_row("Country column", f"{country_column}" if country_column else "(not specified)")
    console.print(table)

    rendered = contest_template.render(
        name=name,
        shortname=shortname,
        start_time=format_datetime(start_str),
        duration=format_duration(duration_str),
        penalty_time=str(penalty_minutes),
        allow_submit=str(allow_submit).lower(),
        teams=teams_path,
        delimiter=repr(delimiter)[1:-1],
        rows=rows,
        name_column=name_column,
        affiliation_column=affiliation_column,
        country_column=country_column,
    )
    return rendered
