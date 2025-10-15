import datetime as dt

from rich.console import Console
from rich.table import Table

from dom.templates.init import contest_template
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

    duration_result = ask(
        "Duration (HH:MM:SS)",
        console=console,
        default="05:00:00",
        parser=ValidatorBuilder.duration_hms().build(),
    )
    if isinstance(duration_result, tuple):
        h, m, s = duration_result
    else:
        # Fallback if not a tuple
        h, m, s = 5, 0, 0
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

    delimiter = ask(
        f"Field delimiter (Enter for default: {suggested_delim!r})",
        console=console,
        default=suggested_delim,
        parser=ValidatorBuilder.string()
        .one_of([",", ";", "\t", "comma", "semicolon", "tab"])
        .replace("comma", ",")
        .replace("semicolon", ";")
        .replace("tab", "\t")
        .build(),
        show_default=False,
    )

    # Summary
    table = Table(title="Contest Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Name", name)
    table.add_row("Shortname", shortname)
    table.add_row(
        "Start time",
        start_dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(start_dt, "strftime") else str(start_dt),
    )
    table.add_row("Duration", duration_str)
    table.add_row("Penalty time", f"{penalty_minutes} minutes")
    table.add_row("Allow submit", "Yes" if allow_submit else "No")
    table.add_row("Teams file", teams_path)
    console.print(table)

    rendered = contest_template.render(
        name=name,
        shortname=shortname,
        start_time=format_datetime(
            start_dt.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(start_dt, "strftime")
            else str(start_dt)
        ),
        duration=format_duration(duration_str),
        penalty_time=str(penalty_minutes),
        allow_submit=str(allow_submit).lower(),
        teams=teams_path,
        delimiter=repr(delimiter)[1:-1],
    )
    return rendered
