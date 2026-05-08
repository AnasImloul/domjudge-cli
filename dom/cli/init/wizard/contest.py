import datetime as dt
from pathlib import Path

from rich.table import Table

from dom import ui
from dom.templates.init import contest_template
from dom.utils.csv_preview import (
    build_csv_preview,
    column_index_parser,
    count_csv_rows,
    get_column_count,
)
from dom.utils.time import format_datetime, format_duration
from dom.utils.validators import ValidatorBuilder


def initialize_contest():
    ui.header("Contest Configuration")
    ui.info("Set up the parameters for your coding contest")

    name = ui.ask(
        "Contest name",
        parser=ValidatorBuilder.string(none_as_empty=True).strip().non_empty().build(),
    )
    shortname = ui.ask(
        "Contest shortname",
        parser=ValidatorBuilder.string(none_as_empty=True).strip().non_empty().build(),
    )

    default_start = (dt.datetime.now() + dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    start_dt = ui.ask(
        "Start time (YYYY-MM-DD HH:MM:SS)",
        default=default_start,
        parser=ValidatorBuilder.datetime("%Y-%m-%d %H:%M:%S").build(),
    )

    h, m, s = ui.ask(
        "Duration (HH:MM:SS)",
        default="05:00:00",
        parser=ValidatorBuilder.duration_hms().build(),
    )
    duration_str = f"{h:02d}:{m:02d}:{s:02d}"

    penalty_minutes = ui.ask(
        "Penalty time (minutes)",
        default="20",
        parser=ValidatorBuilder.integer().positive().build(),
    )

    allow_submit = ui.ask_bool("Allow submissions?", default=True)

    teams_path = ui.ask(
        "Teams file path (CSV/TSV)",
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
    delimiter = ui.ask(
        f"Field delimiter (Enter for default: {suggested_delim!r})",
        default=suggested_delim,
        parser=ValidatorBuilder.string()
        .one_of(delimiter_aliases)
        .map(delimiter_aliases.__getitem__)
        .build(),
        show_default=False,
    )

    ui.header("CSV Preview")
    teams_file_path = Path(teams_path)

    table, has_header = build_csv_preview(
        teams_file_path, delimiter, max_rows=10, show_column_numbers=True
    )
    if table is None:
        ui.warn("Warning: CSV file is empty")
    else:
        ui.render(table)

    confirmed = ui.ask_bool("Does the first row contain headers?", default=has_header)
    if confirmed != has_header:
        has_header = confirmed
        label = "with header" if has_header else "no header"
        ui.header(f"Updated CSV Preview ({label})")
        table, _ = build_csv_preview(
            teams_file_path,
            delimiter,
            max_rows=10,
            show_column_numbers=True,
            has_header=has_header,
        )
        if table is not None:
            ui.render(table)

    num_columns = get_column_count(teams_file_path, delimiter)

    ui.header("Column Mapping")
    ui.info("Specify which columns contain team information (use column numbers from preview)")

    name_column = ui.ask("Name column", default="1", parser=column_index_parser(num_columns))
    affiliation_column = ui.ask(
        "Affiliation column", default="2", parser=column_index_parser(num_columns)
    )
    country_column = ui.ask(
        "Country column (optional, press Enter to skip)",
        default="",
        parser=column_index_parser(num_columns, optional=True),
    )

    total_rows = count_csv_rows(teams_file_path, delimiter)
    start_row = 2 if has_header else 1
    end_row = total_rows
    detected_teams_count = end_row - start_row + 1

    ui.blank()
    ui.success(
        f"Detected {detected_teams_count} teams in rows {start_row}-{end_row}",
        style="bold green",
    )
    rows_confirmed = ui.ask_bool("Is this row range correct?", default=True)

    if not rows_confirmed:
        ui.info("Please specify the correct row range:")
        positive_int = ValidatorBuilder.integer().positive().build()
        start_row = ui.ask("Start row (1-indexed)", default=str(start_row), parser=positive_int)
        end_row = ui.ask("End row (1-indexed)", default=str(end_row), parser=positive_int)

    rows = f"{start_row}-{end_row}"

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
    ui.render(table)

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
