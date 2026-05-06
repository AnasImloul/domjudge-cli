"""Contest plan command."""

from pathlib import Path

import typer

from dom.cli.contest.helpers import load_config_with_secrets
from dom.cli.validators import validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.contest import plan_contest_changes_op
from dom.utils.cli import add_global_options, cli_command


@add_global_options
@cli_command
def plan_command(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """Show what changes would be made to contests without applying them.

    Displays creates/updates per contest, including which fields would change
    and which problems/teams would be added.
    """
    config, secrets = load_config_with_secrets(file, verbose)
    run(plan_contest_changes_op(config), Context(secrets=secrets, verbose=verbose))
