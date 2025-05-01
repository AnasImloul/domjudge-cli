import os
import typer
import datetime
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table

from . import console

init_command = typer.Typer()

INFRA_TEMPLATE = """infra:
  port: {port}
  judges: {judges}
  password: "{password}"
"""

CONTEST_TEMPLATE = """
contests:
  - name: "{name}"
    shortname: "{shortname}"
    start_time: "{start_time}"
    duration: "{duration}"
    penalty_time: {penalty_time}
    allow_submit: {allow_submit}

    problems:
      from: "problems.yaml"

    teams:
      from: "{teams}"
      delimiter: ','
      rows: "2-50"
      name: "$2"
"""

PROBLEMS_TEMPLATE = """- archive: "{archive}"
  platform: "{platform}"
  color: "{color}"
"""

def format_datetime(date_str):
    """Convert datetime string to ISO 8601 format with timezone"""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except ValueError:
        return date_str

def format_duration(duration_str):
    """Format duration to include milliseconds"""
    if "." not in duration_str:
        return duration_str + ".000"
    return duration_str

@init_command.callback(invoke_without_command=True)
def callback():
    """
    Initialize the DOMjudge configuration files with an interactive wizard.
    """
    console.print(Panel.fit("[bold blue]DOMjudge Configuration Wizard[/bold blue]", 
                           subtitle="Create your contest setup"))
    
    # Infrastructure section
    console.print("\n[bold cyan]Infrastructure Configuration[/bold cyan]")
    console.print("Configure the platform settings for your contest environment")
    
    port = Prompt.ask("Port number", default="8080", console=console)
    judges = Prompt.ask("Number of judges", default="2", console=console)
    password = Prompt.ask("Admin password", password=True, console=console)
    
    # Show infrastructure summary
    infra_table = Table(title="Infrastructure Configuration")
    infra_table.add_column("Setting", style="cyan")
    infra_table.add_column("Value", style="green")
    infra_table.add_row("Port", str(port))
    infra_table.add_row("Judges", str(judges))
    infra_table.add_row("Password", "****")
    console.print(infra_table)
    
    infra_content = INFRA_TEMPLATE.format(port=port, judges=judges, password=password)
    
    # Contest section
    console.print("\n[bold cyan]Contest Configuration[/bold cyan]")
    console.print("Set up the parameters for your coding contest")
    
    name = Prompt.ask("Contest name", console=console)
    shortname = Prompt.ask("Contest shortname", console=console)
    
    # Default start time is 1 hour from now
    default_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    start_time = Prompt.ask("Start time (YYYY-MM-DD HH:MM:SS)", default=default_time, console=console)
    duration = Prompt.ask("Duration (HH:MM:SS)", default="5:00:00", console=console)
    penalty_time = Prompt.ask("Penalty time (minutes)", default="20", console=console)
    
    allow_submit = Confirm.ask("Allow submissions?", default=True, console=console)
    allow_submit_str = str(allow_submit).lower()
    
    teams = Prompt.ask("Teams CSV file path", default="teams.csv", console=console)
    
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
    
    contests_content = CONTEST_TEMPLATE.format(
        name=name,
        shortname=shortname,
        start_time=format_datetime(start_time),
        duration=format_duration(duration),
        penalty_time=penalty_time,
        allow_submit=allow_submit_str,
        teams=teams
    )
    
    # Problems section
    console.print("\n[bold cyan]Problems Configuration[/bold cyan]")
    console.print("Add the problems for your contest")
    
    archive = Prompt.ask("Problems directory path", default="./problems", console=console)

    # Normalize path for better cross-platform compatibility
    archive = os.path.normpath(os.path.expanduser(archive))
    console.print(f"Checking directory: [bold]{archive}[/bold]")

    # Check if directory exists with better error handling
    try:
        if not os.path.exists(archive):
            console.print(f"[bold red]Directory not found:[/bold red] {archive}")
            create_dir = Confirm.ask(f"Create directory {archive}?", default=True, console=console)
            if create_dir:
                try:
                    os.makedirs(archive, exist_ok=True)
                    console.print(f"[green]✓ Created directory {archive}[/green]")
                except Exception as e:
                    console.print(f"[bold red]Error creating directory:[/bold red] {str(e)}")
                    raise typer.Exit(code=1)
            else:
                console.print("[yellow]Please create the directory and run this wizard again.[/yellow]")
                raise typer.Exit(code=1)
        else:
            console.print(f"[green]✓ Directory found: {archive}[/green]")
    except Exception as e:
        console.print(f"[bold red]Unexpected error checking directory:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

    # Get problem files
    try:
        problems = [f for f in os.listdir(archive) if os.path.isfile(os.path.join(archive, f))]
        console.print(f"Found {len(problems)} files in directory")
    except Exception as e:
        console.print(f"[bold red]Error listing directory contents:[/bold red] {str(e)}")
        problems = []
    
    if not problems:
        console.print(f"[yellow]No problem files found in {archive}[/yellow]")
        add_dummy = Confirm.ask("Add a sample problem placeholder?", default=False, console=console)
        if add_dummy:
            problems = ["sample_problem.zip"]
        else:
            console.print("[yellow]You'll need to add problem files later.[/yellow]")
            if not Confirm.ask("Continue without problems?", default=True):
                raise typer.Exit(code=1)
    
    platform = Prompt.ask("Platform name", console=console, default="Polygon")
    
    # Problem configurations
    problem_configs = []

    if problems:
        console.print("\n[bold]Problem Colors[/bold]")
        console.print("Choose a unique color for each problem from the DOMjudge color palette")
        
        # DOMjudge supported colors
        domjudge_colors = {
            "red": "#FF0000",
            "green": "#00FF00",
            "blue": "#0000FF",
            "yellow": "#FFFF00",
            "cyan": "#00FFFF",
            "magenta": "#FF00FF",
            "orange": "#FFA500",
            "purple": "#800080",
            "pink": "#FFC0CB",
            "teal": "#008080",
            "brown": "#A52A2A",
            "gray": "#808080",
            "black": "#000000"
        }
        
        used_colors = set()
        
        color_table = Table(title="Available Colors")
        color_table.add_column("Color Name", style="cyan")
        color_table.add_column("Preview", style="bold")
        
        for name, hex_code in domjudge_colors.items():
            color_table.add_row(name, f"[on {hex_code}]      [/]")
        
        console.print(color_table)
        
        for problem in problems:
            available_colors = [name for name, _ in domjudge_colors.items() 
                               if name not in used_colors]
            
            if not available_colors:
                console.print("[yellow]Warning: All colors have been used. Some problems will have duplicate colors.[/yellow]")
                available_colors = list(domjudge_colors.keys())
            
            # Default to the first available color
            default_color = available_colors[0] if available_colors else "black"
            
            console.print(f"\nChoose a color for problem: [bold]{problem}[/bold]")
            console.print("Available colors: " + ", ".join(f"[{color}]{color}[/{color}]" for color in available_colors))
            
            # Let user pick from available colors
            color_name = Prompt.ask(
                "Color", 
                choices=list(domjudge_colors.keys()),
                default=default_color,
                console=console
            )
            
            # Get the hex code for the selected color
            color_hex = domjudge_colors[color_name]
            
            # Mark color as used
            used_colors.add(color_name)
            
            # Display selected color
            console.print(f"Selected: [{color_name}]{color_name}[/{color_name}] ({color_hex})")
            
            problem_configs.append({
                "problem": problem,
                "archive": os.path.join(archive, problem),
                "platform": platform,
                "color": color_hex
            })
    
    # Generate problems.yaml content
    problems_content = ""
    first = True
    for config in problem_configs:
        if not first:
            problems_content += "\n" # Add a newline before the next entry
        problems_content += PROBLEMS_TEMPLATE.format(
            archive=config['archive'],
            platform=config['platform'],
            color=config['color']
        )
        first = False

    # Write files with progress spinner
    console.print("\n[bold cyan]Creating Configuration Files[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        console=console
    ) as progress:
        task = progress.add_task("Writing configuration files...", total=2)
        
        # Write dom-judge.yaml with proper formatting
        with open("dom-judge.yaml", "w") as domjudge_file:
            # Write without trailing newlines to control exact format
            domjudge_file.write(infra_content.strip())
            # Ensure exactly one blank line between sections
            domjudge_file.write("\n\n")
            domjudge_file.write(contests_content.strip())
        progress.update(task, advance=1)
        
        # Write problems.yaml
        if problems:
            with open("problems.yaml", "w") as problems_file:
                problems_file.write(problems_content.strip()) 
                problems_file.write("\n")
        progress.update(task, advance=1)
    
    # Success message with next steps
    console.print("\n[bold green]✓ Success![/bold green] Configuration files created successfully:")
    console.print("  • [bold]dom-judge.yaml[/bold] - Main configuration")
    if problems:
        console.print("  • [bold]problems.yaml[/bold] - Problem definitions")
    
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  1. Run [bold]dom infra apply[/bold] to set up infrastructure")
    console.print("  2. Run [bold]dom contest apply[/bold] to configure the contest")