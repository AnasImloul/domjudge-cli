import os
import typer
from jinja2 import Template

from dom.cli import console
from rich.table import Table
from dom.utils.cli import ask_override_if_exists
from dom.templates.init import problems_template
from dom.utils.color import get_hex_color

from dom.utils.prompt import ask, ask_bool, ask_choice


def check_existing_files() -> str:
    """Check if both .yml and .yaml exist and decide which file to use."""
    yml_exists = os.path.exists("problems.yml")
    yaml_exists = os.path.exists("problems.yaml")

    if yml_exists and yaml_exists:
        console.print("[bold red]Both 'problems.yml' and 'problems.yaml' exist.[/bold red]")
        console.print("[yellow]Please remove one of the files and run this wizard again.[/yellow]")
        raise typer.Exit(code=1)

    return "problems.yml" if yml_exists else "problems.yaml"


def ensure_archive_dir(archive: str) -> str:
    """Ensure the archive directory exists or create it."""
    archive = os.path.normpath(os.path.expanduser(archive))
    console.print(f"Checking directory: [bold]{archive}[/bold]")

    if not os.path.exists(archive):
        console.print(f"[bold red]Directory not found:[/bold red] {archive}")
        if ask_bool(f"Create directory {archive}?", default=True, console=console):
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


def list_problem_files(archive: str) -> list[str]:
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


def choose_problem_colors(problems: list[str]) -> list[tuple[str, str]]:
    """Prompt user to assign colors to problems."""
    all_colors = {
        "red", "green", "blue",
        "yellow", "cyan", "magenta",
        "orange", "purple", "pink",
        "teal", "brown", "gray",
        "black",
    }

    used_colors = set()
    color_table = Table(title="Available Colors")
    color_table.add_column("Color Name", style="cyan")
    color_table.add_column("Preview", style="bold")

    for name, hex_code in map(lambda color: (color, get_hex_color(color)), all_colors):
        color_table.add_row(name, f"[on {hex_code}]      [/]")

    console.print(color_table)

    configs: list[tuple[str, str]] = []
    for problem in problems:
        available_colors = [c for c in all_colors if c not in used_colors] or list(all_colors)
        default_color = available_colors[0]
        console.print(f"\nChoose a color for problem: [bold]{problem}[/bold]")
        console.print("Available colors: " + ", ".join(f"[{c}]{c}[/{c}]" for c in available_colors))

        color_name = ask_choice(
            "Color",
            console=console,
            choices=list(all_colors),
            default=default_color,
        )
        color_hex = get_hex_color(color_name)
        used_colors.add(color_name)

        console.print(f"Selected: [{color_name}]{color_name}[/]{'' if color_name == 'black' else ''} ({color_hex})")
        configs.append((problem, color_hex))

    return configs


def render_problems_yaml(template: Template, archive: str, platform: str, problem_configs: list[tuple[str, str]]) -> str:
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
        return None

    archive = ask("Problems directory path", default="./problems", console=console)
    archive = ensure_archive_dir(archive)
    problems = list_problem_files(archive)

    if not problems:
        console.print(f"[yellow]No problem files found in {archive}[/yellow]")
        if not ask_bool("Continue without problems?", default=True, console=console):
            raise typer.Exit(code=1)

    platform = ask("Platform name", console=console, default="Polygon")

    problem_configs: list[tuple[str, str]] = []
    if problems:
        problem_configs = choose_problem_colors(problems)

    problems_content = render_problems_yaml(problems_template, archive, platform, problem_configs)

    if problems:
        return problems_content.strip() + "\n"
    return None
