import typer

from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.init import InitializeProjectOperation
from dom.utils.cli import add_global_options, cli_command, get_secrets_manager

init_command = typer.Typer()


@init_command.callback(invoke_without_command=True)
@add_global_options
@cli_command
def callback(
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what files would be created without actually creating them",
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
):
    """
    Initialize the DOMjudge configuration files with an interactive wizard.

    Use --dry-run to preview what files would be created without actually creating them.
    """
    OperationRunner(
        operation=InitializeProjectOperation(overwrite=overwrite),
        show_progress=False,
    ).run(context=OperationContext(secrets=get_secrets_manager(), dry_run=dry_run, verbose=verbose))
