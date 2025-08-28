import os
import typer
from dom.cli import console
from dom.core.services.init.contest import initialize_contest
from dom.core.services.init.infra import initialize_infrastructure
from dom.core.services.init.problems import initialize_problems
from dom.utils.cli import check_file_exists
from rich.panel import Panel


def callback(overwrite: bool):
    console.print(Panel.fit("[bold blue]DOMjudge Configuration Wizard[/bold blue]",
                            subtitle="Create your contest setup"))
    if not overwrite:
        check_file_exists("dom-judge.yaml")
        check_file_exists("dom-judge.yml")

    domjudge_output_file = "dom-judge.yml" if os.path.exists("dom-judge.yml") else "dom-judge.yaml"
    problems_output_file = "problems.yml" if os.path.exists("problems.yml") else "problems.yaml"

    infra_content = initialize_infrastructure()
    contests_content = initialize_contest()
    problems_content = initialize_problems()

    console.print("\n[bold cyan]Creating Configuration Files[/bold cyan]")

    with open(domjudge_output_file, "w") as domjudge_file:
        domjudge_file.write(infra_content.strip())
        domjudge_file.write("\n\n")
        domjudge_file.write(contests_content.strip())

    if problems_content:
        with open(problems_output_file, "w") as problems_file:
            problems_file.write(problems_content.strip())
            problems_file.write("\n")

    console.print("\n[bold green]✓ Success![/bold green] Configuration files created successfully:")
    console.print("  • [bold]dom-judge.yaml[/bold] - Main configuration")
    if problems_content:
        console.print("  • [bold]problems.yaml[/bold] - Problem definitions")
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  1. Run [bold]dom infra apply[/bold] to set up infrastructure")
    console.print("  2. Run [bold]dom contest apply[/bold] to configure the contest")