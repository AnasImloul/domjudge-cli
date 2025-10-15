from pathlib import Path

import typer

from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import (
    ApplyInfrastructureOperation,
    DestroyInfrastructureOperation,
    LoadInfraConfigOperation,
    PrintInfrastructureStatusOperation,
)
from dom.exceptions import DomJudgeCliError
from dom.logging_config import get_logger
from dom.utils.cli import get_secrets_manager

logger = get_logger(__name__)
infra_command = typer.Typer()


@infra_command.command("apply")
def apply_from_config(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
) -> None:
    """
    Apply configuration to infrastructure and platform.
    """
    try:
        # Create execution context
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets)

        # Load configuration
        load_runner = OperationRunner(LoadInfraConfigOperation(file))
        load_result = load_runner.run(context)

        if not load_result.is_success():
            raise typer.Exit(code=1)

        # Apply infrastructure
        config = load_result.unwrap()
        apply_runner = OperationRunner(ApplyInfrastructureOperation(config))
        apply_result = apply_runner.run(context)

        if not apply_result.is_success():
            raise typer.Exit(code=1)

    except DomJudgeCliError as e:
        logger.error(f"Failed to apply infrastructure: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.error(f"Unexpected error applying infrastructure: {e}", exc_info=True)
        raise typer.Exit(code=1) from e


@infra_command.command("destroy")
def destroy_all(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destruction"),
) -> None:
    """
    Destroy all infrastructure and platform resources.

    WARNING: This will permanently remove all containers, volumes, and data.
    """
    if not confirm:
        typer.echo("❗ Use --confirm to actually destroy infrastructure.")
        typer.echo("   This action is irreversible and will delete all data.")
        raise typer.Exit(code=1)

    try:
        # Create execution context
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets)

        # Destroy infrastructure
        runner = OperationRunner(DestroyInfrastructureOperation())
        result = runner.run(context)

        if not result.is_success():
            raise typer.Exit(code=1)

    except DomJudgeCliError as e:
        logger.error(f"Failed to destroy infrastructure: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.error(f"Unexpected error destroying infrastructure: {e}", exc_info=True)
        raise typer.Exit(code=1) from e


@infra_command.command("status")
def check_status(
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
    try:
        # Load config if provided (to know expected judgehost count)
        config = None
        if file:
            load_runner = OperationRunner(LoadInfraConfigOperation(file), show_progress=False)
            secrets = get_secrets_manager()
            context = OperationContext(secrets=secrets)
            load_result = load_runner.run(context)

            if load_result.is_success():
                config = load_result.unwrap()

        # Check and print infrastructure status
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets)

        # Use unified operation that checks and prints
        print_status_runner = OperationRunner(
            PrintInfrastructureStatusOperation(config, json_output=json_output),
            show_progress=False,
            silent=True,
        )
        result = print_status_runner.run(context)

        if not result.is_success():
            raise typer.Exit(code=1)

    except DomJudgeCliError as e:
        logger.error(f"Failed to check infrastructure status: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.error(f"Unexpected error checking infrastructure status: {e}", exc_info=True)
        raise typer.Exit(code=1) from e
