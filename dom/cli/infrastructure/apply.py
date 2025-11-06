"""Infrastructure apply command."""

from pathlib import Path

import typer

from dom.cli.infrastructure.helpers import load_infra_config_with_secrets
from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import ApplyInfrastructureOperation
from dom.utils.cli import add_global_options, cli_command


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
    """
    Apply configuration to infrastructure and platform.

    Use --dry-run to preview what changes would be made without actually applying them.
    """
    # Load configuration (always runs, even in dry-run mode, since it's read-only)
    config, secrets = load_infra_config_with_secrets(file, verbose)

    # Apply infrastructure with context (operations handle dry-run)
    apply_context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)
    apply_runner = OperationRunner(ApplyInfrastructureOperation(config))
    apply_result = apply_runner.run(apply_context)

    # Don't treat dry-run (skipped) as failure
    if apply_result.is_failure():
        raise typer.Exit(code=1)
