"""Infrastructure status command."""

from pathlib import Path

import typer

from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import PrintInfrastructureStatusOperation
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
    """
    Check the health status of DOMjudge infrastructure.

    This command checks:
    - Docker daemon availability
    - DOMserver container status
    - MariaDB container status
    - Judgehost containers status
    - MySQL client container status

    Returns exit code 0 if all systems healthy, 1 otherwise.
    Useful for CI/CD pipelines and automation scripts.
    """
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, verbose=verbose)

    print_status_runner = OperationRunner(
        PrintInfrastructureStatusOperation(json_output=json_output),
        show_progress=False,
        silent=True,
    )
    result = print_status_runner.run(context)

    if result.is_failure():
        raise typer.Exit(code=1)
