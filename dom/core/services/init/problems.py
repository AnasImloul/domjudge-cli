from pathlib import Path

import typer
from jinja2 import Template
from rich.console import Console
from rich.table import Table

from dom.templates.init import problems_template
from dom.utils.cli import ask_override_if_exists
from dom.utils.color import get_hex_color
from dom.utils.prompt import ask, ask_bool, ask_choice

console = Console()


def check_existing_files() -> str:
    """Check if both .yml and .yaml exist and decide which file to use."""
    yml_exists = Path("problems.yml").exists()
    yaml_exists = Path("problems.yaml").exists()

    if yml_exists and yaml_exists:
        console.print("[bold red]Both 'problems.yml' and 'problems.yaml' exist.[/bold red]")
        console.print("[yellow]Please remove one of the files and run this wizard again.[/yellow]")
        raise typer.Exit(code=1)

    return "problems.yml" if yml_exists else "problems.yaml"


def ensure_archive_dir(archive: str) -> str:
    """Ensure the archive directory exists or create it."""
    archive_path = Path(archive).expanduser().resolve()
    console.print(f"Checking directory: [bold]{archive_path}[/bold]")

    if not archive_path.exists():
        console.print(f"[bold red]Directory not found:[/bold red] {archive_path}")
        if ask_bool(f"Create directory {archive_path}?", default=True, console=console):
            try:
                archive_path.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓ Created directory {archive_path}[/green]")
            except Exception as e:
                console.print(f"[bold red]Error creating directory:[/bold red] {e!s}")
                raise typer.Exit(code=1) from e
        else:
            console.print("[yellow]Please create the directory and run this wizard again.[/yellow]")
            raise typer.Exit(code=1) from None
    else:
        console.print(f"[green]✓ Directory found: {archive_path}[/green]")

    return str(archive_path)


def list_problem_files(archive: str) -> list[str]:
    """List .zip files in the archive directory."""
    try:
        archive_path = Path(archive)
        problems = [
            f.name
            for f in archive_path.iterdir()
            if f.is_file() and f.name.lower().endswith(".zip") and not f.name.startswith(".")
        ]
        console.print(f"Found {len(problems)} files in directory")
        return problems
    except Exception as e:
        console.print(f"[bold red]Error listing directory contents:[/bold red] {e!s}")
        return []


def choose_problem_colors(problems: list[str]) -> list[tuple[str, str]]:
    """Prompt user to assign colors to problems."""
    all_colors = {
        "red",
        "green",
        "blue",
        "yellow",
        "cyan",
        "magenta",
        "orange",
        "purple",
        "pink",
        "teal",
        "brown",
        "gray",
        "black",
    }

    used_colors = set()
    color_table = Table(title="Available Colors")
    color_table.add_column("Color Name", style="cyan")
    color_table.add_column("Preview", style="bold")

    for name, hex_code in ((color, get_hex_color(color)) for color in all_colors):
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

        console.print(f"Selected: [{color_name}]{color_name}[/] ({color_hex})")
        configs.append((problem, color_hex))

    return configs


def render_problems_yaml(
    template: Template, archive: str, platform: str, problem_configs: list[tuple[str, str]]
) -> str:
    """Render problems.yaml content from Jinja template and problem configs."""
    parts = []
    for problem, color in problem_configs:
        archive_path = str(Path(archive) / problem)
        parts.append(template.render(archive=archive_path, platform=platform, color=color))
    return "\n\n".join(parts)


def initialize_problems():
    console.print("\n[bold cyan]Problems Configuration[/bold cyan]")
    console.print("Add the problems for your contest")

    output_file = check_existing_files()
    if not ask_override_if_exists(Path(output_file)):
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
