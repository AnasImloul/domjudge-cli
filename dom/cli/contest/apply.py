"""Contest apply command."""

from pathlib import Path

import typer

from dom.cli.contest.helpers import load_config_with_secrets
from dom.cli.contest.render import render_apply_warnings
from dom.cli.decorators import add_global_options, cli_command
from dom.cli.validators import validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.contest import apply_contests_op


@add_global_options
@cli_command
def apply_command(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """Apply configuration to contests on the platform.

    Use ``--dry-run`` to preview the steps that would run.
    """
    config, secrets = load_config_with_secrets(file, verbose)
    results = run(
        apply_contests_op(config), Context(secrets=secrets, dry_run=dry_run, verbose=verbose)
    )
    if results:
        render_apply_warnings(results)
