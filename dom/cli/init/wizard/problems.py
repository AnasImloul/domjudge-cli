from pathlib import Path

import typer
from jinja2 import Template
from rich.table import Table

from dom import ui
from dom.templates.init import problems_template
from dom.utils.cli import ask_override_if_exists
from dom.utils.color import get_hex_color


def check_existing_files() -> str:
    """Check if both .yml and .yaml exist and decide which file to use."""
    yml_exists = Path("problems.yml").exists()
    yaml_exists = Path("problems.yaml").exists()

    if yml_exists and yaml_exists:
        ui.error("Both 'problems.yml' and 'problems.yaml' exist.", style="bold red")
        ui.warn("Please remove one of the files and run this wizard again.")
        raise typer.Exit(code=1)

    return "problems.yml" if yml_exists else "problems.yaml"


def ensure_archive_dir(archive: str) -> str:
    """Ensure the archive directory exists or create it."""
    archive_path = Path(archive).expanduser().resolve()
    ui.write(f"Checking directory: [bold]{archive_path}[/bold]")

    if not archive_path.exists():
        ui.error(f"Directory not found: {archive_path}", style="bold red")
        if ui.ask_bool(f"Create directory {archive_path}?", default=True):
            try:
                archive_path.mkdir(parents=True, exist_ok=True)
                ui.success(f"+ Created directory {archive_path}")
            except Exception as e:
                ui.error(f"Error creating directory: {e!s}", style="bold red")
                raise typer.Exit(code=1) from e
        else:
            ui.warn("Please create the directory and run this wizard again.")
            raise typer.Exit(code=1) from None
    else:
        ui.success(f"+ Directory found: {archive_path}")

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
        ui.info(f"Found {len(problems)} files in directory")
        return problems
    except Exception as e:
        ui.error(f"Error listing directory contents: {e!s}", style="bold red")
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

    ui.render(color_table)

    configs: list[tuple[str, str]] = []
    for problem in problems:
        available_colors = [c for c in all_colors if c not in used_colors] or list(all_colors)
        default_color = available_colors[0]
        ui.write(f"\nChoose a color for problem: [bold]{problem}[/bold]")
        ui.info("Available colors: " + ", ".join(f"[{c}]{c}[/{c}]" for c in available_colors))

        color_name = ui.ask_choice(
            "Color",
            choices=list(all_colors),
            default=default_color,
        )
        color_hex = get_hex_color(color_name)
        used_colors.add(color_name)

        ui.write(f"Selected: [{color_name}]{color_name}[/] ({color_hex})")
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
    ui.header("Problems Configuration")
    ui.info("Add the problems for your contest")

    output_file = check_existing_files()
    if not ask_override_if_exists(Path(output_file)):
        return None

    archive = ui.ask("Problems directory path", default="./problems")
    archive = ensure_archive_dir(archive)
    problems = list_problem_files(archive)

    if not problems:
        ui.warn(f"No problem files found in {archive}")
        if not ui.ask_bool("Continue without problems?", default=True):
            raise typer.Exit(code=1)

    platform = ui.ask("Platform name", default="Polygon")

    problem_configs: list[tuple[str, str]] = []
    if problems:
        problem_configs = choose_problem_colors(problems)

    problems_content = render_problems_yaml(problems_template, archive, platform, problem_configs)

    if problems:
        return problems_content.strip() + "\n"
    return None
