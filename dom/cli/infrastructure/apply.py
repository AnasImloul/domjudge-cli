"""Infrastructure apply command."""

from pathlib import Path

import typer

from dom import ui
from dom.cli.decorators import add_global_options, cli_command
from dom.cli.infrastructure.helpers import load_infra_config_with_secrets
from dom.cli.validators import validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.infrastructure import apply_infrastructure_op
from dom.utils.prerequisites import is_privileged_port


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
    """Apply configuration to infrastructure and platform.

    Use ``--dry-run`` to preview the steps that would run.
    """
    config, secrets = load_infra_config_with_secrets(file, verbose)
    if is_privileged_port(config.port):
        ui.warn(f"** Warning: Port {config.port} is privileged (< 1024)")
        ui.warn("   You may need to run with sudo or use a port >= 1024")
        ui.blank()
    run(
        apply_infrastructure_op(config),
        Context(secrets=secrets, dry_run=dry_run, verbose=verbose),
    )
