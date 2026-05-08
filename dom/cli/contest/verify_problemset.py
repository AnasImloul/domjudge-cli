"""Contest verify-problemset command."""

from pathlib import Path

import typer

from dom.cli.decorators import add_global_options, cli_command
from dom.cli.validators import validate_contest_name, validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.contest import verify_problemset_op
from dom.utils.project import get_secrets_manager


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
    """Verify the problemset of the specified contest against the platform.

    Use ``--dry-run`` to preview without actually performing the verification.
    """
    secrets = get_secrets_manager()
    ctx = Context(secrets=secrets, dry_run=dry_run, verbose=verbose)
    run(verify_problemset_op(file, contest), ctx)
