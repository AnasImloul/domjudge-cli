import typer
from dom.core.services.init import callback as init_callback



init_command = typer.Typer()

@init_command.callback(invoke_without_command=True)
def callback(overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files")):
    """
    Initialize the DOMjudge configuration files with an interactive wizard.
    """
    init_callback(overwrite=overwrite)
