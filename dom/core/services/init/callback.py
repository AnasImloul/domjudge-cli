from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from dom.core.services.init.contest import initialize_contest
from dom.core.services.init.infra import initialize_infrastructure
from dom.core.services.init.problems import initialize_problems
from dom.utils.cli import check_file_exists

console = Console()


def callback(overwrite: bool):
    console.print(
        Panel.fit(
            "[bold blue]DOMjudge Configuration Wizard[/bold blue]",
            subtitle="Create your contest setup",
        )
    )
    if not overwrite:
        check_file_exists(Path("dom-judge.yaml"))
        check_file_exists(Path("dom-judge.yml"))

    domjudge_output_file = "dom-judge.yml" if Path("dom-judge.yml").exists() else "dom-judge.yaml"
    problems_output_file = "problems.yml" if Path("problems.yml").exists() else "problems.yaml"

    infra_content = initialize_infrastructure()
    contests_content = initialize_contest()
    problems_content = initialize_problems()

    console.print("\n[bold cyan]Creating Configuration Files[/bold cyan]")

    Path(domjudge_output_file).write_text(infra_content.strip() + "\n\n" + contests_content.strip())

    if problems_content:
        Path(problems_output_file).write_text(problems_content.strip() + "\n")

    console.print("\n[bold green]✓ Success![/bold green] Configuration files created successfully:")
    console.print("  • [bold]dom-judge.yaml[/bold] - Main configuration")
    if problems_content:
        console.print("  • [bold]problems.yaml[/bold] - Problem definitions")
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  1. Run [bold]dom infra apply[/bold] to set up infrastructure")
    console.print("  2. Run [bold]dom contest apply[/bold] to configure the contest")
