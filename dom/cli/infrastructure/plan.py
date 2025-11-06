"""Infrastructure plan command."""

from pathlib import Path

import typer

from dom.cli.infrastructure.helpers import load_infra_config_with_secrets
from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import PlanInfraChangesOperation
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
    Show what changes would be made to infrastructure without applying them.

    This command analyzes your configuration and displays:
    - Whether infrastructure needs to be created or updated
    - Whether changes are safe for live infrastructure (e.g., scaling judges)
    - Whether changes require full restart (e.g., port changes)

    This helps you understand the impact of changes before applying them.
    """
    # Load configuration
    config, secrets = load_infra_config_with_secrets(file, verbose)

    # Plan changes
    plan_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    plan_runner = OperationRunner(PlanInfraChangesOperation(config), show_progress=False)
    plan_result = plan_runner.run(plan_context)

    if plan_result.is_failure():
        raise typer.Exit(code=1)
