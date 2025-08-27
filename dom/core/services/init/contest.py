import os
from dom.cli import console
import datetime
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from jinja2 import Environment, PackageLoader, select_autoescape

from dom.utils.time import format_datetime, format_duration

def initialize_contest():
    console.print("\n[bold cyan]Contest Configuration[/bold cyan]")
    console.print("Set up the parameters for your coding contest")


    output_file = os.path.join(os.getcwd(), "dom-judge.yaml")

    env = Environment(
        loader=PackageLoader("dom", "templates"),
        autoescape=select_autoescape()
    )

    template = env.get_template("init/contest.yml.j2")
    
    while True:
        name = Prompt.ask("Contest name", console=console)
        if name.strip():
            break
        console.print("[red]Contest name cannot be empty.[/red]")

    while True:
        shortname = Prompt.ask("Contest shortname", console=console)
        if shortname.strip():
            break
        console.print("[red]Contest shortname cannot be empty.[/red]")

    # Default start time is 1 hour from now
    default_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    while True:
        start_time = Prompt.ask("Start time (YYYY-MM-DD HH:MM:SS)", default=default_time, console=console)
        try:
            datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            break
        except ValueError:
            console.print("[red]Invalid start time format. Use YYYY-MM-DD HH:MM:SS[/red]")

    while True:
        duration = Prompt.ask("Duration (HH:MM:SS)", default="05:00:00", console=console)
        try:
            duration_parts = duration.split(":")
            if len(duration_parts) != 3:
                raise ValueError()
            hours, minutes, seconds = map(int, duration_parts)
            if hours > 0 or minutes > 0 or seconds > 0:
                break
            raise ValueError()
        except ValueError:
            console.print("[red]Duration must be greater than 0 seconds[/red]")

    while True:
        penalty_time = Prompt.ask("Penalty time (minutes)", default="20", console=console)
        if penalty_time.isdigit() and int(penalty_time) > 0:
            break
        console.print("[red]Penalty time must be a positive integer.[/red]")

    allow_submit = Confirm.ask("Allow submissions?", default=True, console=console)
    allow_submit_str = str(allow_submit).lower()

    while True:
        teams = Prompt.ask("Teams file path (CSV/TSV)", default="teams.csv", console=console)
        
        # Check if file exists
        if not os.path.isfile(teams):
            console.print(f"[red]File '{teams}' does not exist. Please provide a valid file path.[/red]")
            continue
            
        # Validate file extension
        ext = os.path.splitext(teams)[1].lower()
        if ext not in ('.csv', '.tsv'):
            console.print(f"[red]Unsupported file extension '{ext}'. Please use .csv or .tsv files.[/red]")
            continue
            
        # Ask for delimiter with default
        default_delimiter = '\\t' if ext == '.tsv' else ','
        delimiter = Prompt.ask(
            f"Enter field delimiter (press Enter for default: '{default_delimiter}' for {ext[1:].upper()} files)",
            default=default_delimiter,
            show_default=False,
            console=console
        )
        
        # Handle special delimiter names
        if delimiter.lower() == 'tab':
            delimiter = '\t'
        elif delimiter.lower() == 'comma':
            delimiter = ','
        elif delimiter.lower() == 'semicolon':
            delimiter = ';'
            
        break
    
    # Contest summary
    contest_table = Table(title="Contest Configuration")
    contest_table.add_column("Setting", style="cyan")
    contest_table.add_column("Value", style="green")
    contest_table.add_row("Name", name)
    contest_table.add_row("Shortname", shortname)
    contest_table.add_row("Start time", start_time)
    contest_table.add_row("Duration", duration)
    contest_table.add_row("Penalty time", f"{penalty_time} minutes")
    contest_table.add_row("Allow submit", "Yes" if allow_submit else "No")
    contest_table.add_row("Teams file", teams)
    console.print(contest_table)

    rendered = template.render(
        name=name,
        shortname=shortname,
        start_time=format_datetime(start_time),
        duration=format_duration(duration),
        penalty_time=penalty_time,
        allow_submit=allow_submit_str,
        teams=teams,
        delimiter=delimiter
    )
    
    with open(output_file, "a") as f:
        f.write(rendered)