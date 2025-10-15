import typer

from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.init import InitializeProjectOperation
from dom.utils.cli import cli_command, get_secrets_manager

init_command = typer.Typer()


@init_command.callback(invoke_without_command=True)
@cli_command
def callback(overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files")):
    """
    Initialize the DOMjudge configuration files with an interactive wizard.
    """
    OperationRunner(
        operation=InitializeProjectOperation(overwrite=overwrite),
        show_progress=False,
    ).run(context=OperationContext(secrets=get_secrets_manager()))
