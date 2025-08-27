from dom.cli import console
from rich.prompt import Prompt, Confirm
from rich.table import Table
import os
import typer
from jinja2 import Environment, PackageLoader, select_autoescape

from dom.utils.cli import ask_override_if_exists


def check_existing_files():
    """Check if both .yml and .yaml exist and decide which file to use."""

    if os.path.exists("problems.yml") and os.path.exists("problems.yaml"):
        console.print("[bold red]Both 'problems.yml' and 'problems.yaml' exist.[/bold red]")
        console.print("[yellow]Please remove one of the files and run this wizard again.[/yellow]")
        raise typer.Exit(code=1)

    return "problems.yml" if os.path.exists("problems.yml") else "problems.yaml"




def ensure_archive_dir(archive: str) -> str:
    """Ensure the archive directory exists or create it."""

    archive = os.path.normpath(os.path.expanduser(archive))
    console.print(f"Checking directory: [bold]{archive}[/bold]")

    if not os.path.exists(archive):
        console.print(f"[bold red]Directory not found:[/bold red] {archive}")
        if Confirm.ask(f"Create directory {archive}?", default=True, console=console):
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

    return archive


def list_problem_files(archive: str):
    """List .zip files in the archive directory."""

    try:
        problems = [
            f for f in os.listdir(archive)
            if os.path.isfile(os.path.join(archive, f))
            and f.lower().endswith(".zip")
            and not f.startswith(".")
        ]
        console.print(f"Found {len(problems)} files in directory")
        return problems
    except Exception as e:
        console.print(f"[bold red]Error listing directory contents:[/bold red] {str(e)}")
        return []


def choose_problem_colors(problems):
    """Prompt user to assign colors to problems."""
    domjudge_colors = {
        "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
        "yellow": "#FFFF00", "cyan": "#00FFFF", "magenta": "#FF00FF",
        "orange": "#FFA500", "purple": "#800080", "pink": "#FFC0CB",
        "teal": "#008080", "brown": "#A52A2A", "gray": "#808080",
        "black": "#000000", 
    }

    used_colors = set()
    color_table = Table(title="Available Colors")
    color_table.add_column("Color Name", style="cyan")
    color_table.add_column("Preview", style="bold")

    for name, hex_code in domjudge_colors.items():
        color_table.add_row(name, f"[on {hex_code}]      [/]")

    console.print(color_table)

    configs = []
    for problem in problems:
        available_colors = [c for c in domjudge_colors if c not in used_colors] or list(domjudge_colors.keys())
        default_color = available_colors[0]
        console.print(f"\nChoose a color for problem: [bold]{problem}[/bold]")
        console.print("Available colors: " + ", ".join(f"[{c}]{c}[/{c}]" for c in available_colors))

        color_name = Prompt.ask("Color", choices=list(domjudge_colors.keys()), default=default_color, console=console)
        color_hex = domjudge_colors[color_name]
        used_colors.add(color_name)

        console.print(f"Selected: [{color_name}]{color_name}[/{color_name}] ({color_hex})")
        configs.append((problem, color_hex))

    return configs


def render_problems_yaml(template, archive, platform, problem_configs):
    """Render problems.yaml content from Jinja template and problem configs."""
    parts = []
    for problem, color in problem_configs:
        parts.append(template.render(archive=os.path.join(archive, problem), platform=platform, color=color))
    return "\n\n".join(parts)


def initialize_problems():
    console.print("\n[bold cyan]Problems Configuration[/bold cyan]")
    console.print("Add the problems for your contest")

    output_file = check_existing_files()
    if not ask_override_if_exists(output_file):
        return

    archive = Prompt.ask("Problems directory path", default="./problems", console=console)
    archive = ensure_archive_dir(archive)
    problems = list_problem_files(archive)

    if not problems:
        console.print(f"[yellow]No problem files found in {archive}[/yellow]")
        if not Confirm.ask("Continue without problems?", default=True):
            raise typer.Exit(code=1)

    platform = Prompt.ask("Platform name", console=console, default="Polygon")

    env = Environment(loader=PackageLoader("dom", "templates"), autoescape=select_autoescape())
    template = env.get_template("init/problems.yml.j2")

    problem_configs = []
    if problems:
        problem_configs = choose_problem_colors(problems)

    problems_content = render_problems_yaml(template, archive, platform, problem_configs)

    console.print("\n[bold cyan]Creating Configuration Files[/bold cyan]")
    if problems:
        with open(output_file, "w") as f:
            f.write(problems_content.strip() + "\n")

    console.print("\n[bold green]✓ Success![/bold green] Configuration files created successfully:")
    console.print("  • [bold]dom-judge.yaml[/bold] - Main configuration")
    if problems:
        console.print("  • [bold]problems.yaml[/bold] - Problem definitions")
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  1. Run [bold]dom infra apply[/bold] to set up infrastructure")
    console.print("  2. Run [bold]dom contest apply[/bold] to configure the contest")
