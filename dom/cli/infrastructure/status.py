"""Infrastructure status command."""

from pathlib import Path

import typer

from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import (
    LoadInfraConfigOperation,
    PrintInfrastructureStatusOperation,
)
from dom.utils.cli import add_global_options, cli_command, get_secrets_manager


@add_global_options
@cli_command
def status_command(
    file: Path = typer.Option(
        None,
        "-f",
        "--file",
        help="Path to configuration YAML file (optional, for expected judgehost count)",
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
    # Load config if provided (to know expected judgehost count)
    config = None
    secrets = get_secrets_manager()

    if file:
        load_runner = OperationRunner(LoadInfraConfigOperation(file), show_progress=False)
        context = OperationContext(secrets=secrets, verbose=verbose)
        load_result = load_runner.run(context)

        if load_result.is_success():
            config = load_result.unwrap()

    # Check and print infrastructure status
    context = OperationContext(secrets=secrets, verbose=verbose)

    # Use unified operation that checks and prints
    print_status_runner = OperationRunner(
        PrintInfrastructureStatusOperation(config, json_output=json_output),
        show_progress=False,
        silent=True,
    )
    result = print_status_runner.run(context)

    # Failure means health check failed
    if result.is_failure():
        raise typer.Exit(code=1)
