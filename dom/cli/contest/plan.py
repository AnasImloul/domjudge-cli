"""Contest plan command."""

from pathlib import Path

import typer

from dom.cli.contest.helpers import load_config_with_secrets
from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.contest import PlanContestChangesOperation
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
    """
    Show what changes would be made to contests without applying them.

    This command analyzes your configuration and displays:
    - Which contests would be created
    - Which contests would be updated and what fields would change
    - Which problems/teams would be added

    This is more detailed than --dry-run and shows actual differences
    between current state and desired configuration.
    """
    # Load configuration
    config, secrets = load_config_with_secrets(file, verbose)

    # Plan changes
    plan_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    plan_runner = OperationRunner(PlanContestChangesOperation(config), show_progress=False)
    plan_result = plan_runner.run(plan_context)

    if plan_result.is_failure():
        raise typer.Exit(code=1)
