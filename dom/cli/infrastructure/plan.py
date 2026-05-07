"""Infrastructure plan command."""

from pathlib import Path

import typer

from dom.cli.decorators import add_global_options, cli_command
from dom.cli.infrastructure.helpers import load_infra_config_with_secrets
from dom.cli.infrastructure.render import render_planned_changes
from dom.cli.validators import validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.infrastructure import plan_infra_changes_op


@add_global_options
@cli_command
def plan_command(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """Show what changes would be made to infrastructure without applying them.

    Reports whether changes are safe for live infrastructure (e.g., scaling
    judges) or require a full restart (e.g., port changes).
    """
    config, secrets = load_infra_config_with_secrets(file, verbose)
    change_set = run(plan_infra_changes_op(config), Context(secrets=secrets, verbose=verbose))
    render_planned_changes(change_set)
