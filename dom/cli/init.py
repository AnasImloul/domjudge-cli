import typer
from dom.cli import console
from dom.core.services.init.contest import initialize_contest
from dom.core.services.init.infra import initialize_infrastructure
from dom.core.services.init.problems import initialize_problems
from dom.utils.cli import check_file_exists
from rich.panel import Panel


init_command = typer.Typer()

@init_command.callback(invoke_without_command=True)
def callback(overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files")):
    """
    Initialize the DOMjudge configuration files with an interactive wizard.
    """
    
    console.print(Panel.fit("[bold blue]DOMjudge Configuration Wizard[/bold blue]", 
                           subtitle="Create your contest setup"))
    if not overwrite:
        check_file_exists("dom-judge.yaml")
        check_file_exists("dom-judge.yml")

    initialize_infrastructure()
    initialize_contest()
    initialize_problems()
