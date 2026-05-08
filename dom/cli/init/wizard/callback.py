from pathlib import Path

from rich.panel import Panel

from dom import ui
from dom.cli.init.wizard.contest import initialize_contest
from dom.cli.init.wizard.infra import initialize_infrastructure
from dom.cli.init.wizard.problems import initialize_problems
from dom.utils.project import check_file_exists


def run_wizard(overwrite: bool) -> None:
    ui.render(
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

    ui.header("Creating Configuration Files")

    Path(domjudge_output_file).write_text(infra_content.strip() + "\n\n" + contests_content.strip())

    if problems_content:
        Path(problems_output_file).write_text(problems_content.strip() + "\n")

    ui.blank()
    ui.success("+ Success! Configuration files created successfully:", style="bold green")
    ui.write("  • [bold]dom-judge.yaml[/bold] - Main configuration")
    if problems_content:
        ui.write("  • [bold]problems.yaml[/bold] - Problem definitions")
    ui.header("Next Steps:")
    ui.write("  1. Run [bold]dom infra apply[/bold] to set up infrastructure")
    ui.write("  2. Run [bold]dom contest apply[/bold] to configure the contest")
