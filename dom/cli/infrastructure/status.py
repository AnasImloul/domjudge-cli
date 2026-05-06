"""Infrastructure status command."""

from pathlib import Path

import typer

from dom.cli.validators import validate_file_path
from dom.core.operations import Context, run
from dom.core.operations.infrastructure import print_infra_status_op
from dom.utils.cli import add_global_options, cli_command, get_secrets_manager


@add_global_options
@cli_command
def status_command(
    file: Path = typer.Option(  # noqa: ARG001
        None,
        "-f",
        "--file",
        help="Path to configuration YAML file (currently unused; reserved for future use)",
        callback=validate_file_path,
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output in JSON format instead of human-readable"
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """Check the health status of DOMjudge infrastructure.

    Returns exit code 0 if all systems healthy, 1 otherwise.
    """
    secrets = get_secrets_manager()
    status = run(
        print_infra_status_op(json_output=json_output),
        Context(secrets=secrets, verbose=verbose),
    )
    if status is not None and not status.is_healthy():
        raise typer.Exit(code=1)
