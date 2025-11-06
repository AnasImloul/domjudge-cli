"""Contest verify-problemset command."""

from pathlib import Path

import typer

from dom.cli.validators import validate_contest_name, validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.contest import VerifyProblemsetOperation
from dom.utils.cli import add_global_options, cli_command, get_secrets_manager


@add_global_options
@cli_command
def verify_problemset_command(
    contest: str = typer.Argument(
        ..., help="Name of the contest to verify its problemset", callback=validate_contest_name
    ),
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview what would be verified without actually verifying"
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Verify the problemset of the specified contest.

    This checks whether the submissions associated with the contest match the expected configuration.
    Use --dry-run to preview what would be checked without actually performing the verification.
    """
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)

    # Verify problemset using operation (disable progress bar since verification has its own)
    verify_runner = OperationRunner(VerifyProblemsetOperation(file, contest), show_progress=False)
    verify_runner.run(context)
