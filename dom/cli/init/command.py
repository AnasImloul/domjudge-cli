"""Init command implementation."""

import typer

from dom.cli.helpers import add_global_options, cli_command, get_secrets_manager
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.init import InitializeProjectOperation


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
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)

    # Run operation (operations handle dry-run)
    runner = OperationRunner(
        operation=InitializeProjectOperation(overwrite=overwrite),
        show_progress=False,
    )
    result = runner.run(context)

    # Don't treat dry-run (skipped) as failure
    if result.is_failure():
        raise typer.Exit(code=1)
