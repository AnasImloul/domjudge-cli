from pathlib import Path

import typer
from rich.prompt import Confirm

from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import (
    ApplyInfrastructureOperation,
    DestroyInfrastructureOperation,
    LoadInfraConfigOperation,
    PrintInfrastructureStatusOperation,
)
from dom.exceptions import DomJudgeCliError
from dom.logging_config import console, get_logger
from dom.utils.cli import add_global_options, cli_command, get_secrets_manager

logger = get_logger(__name__)
infra_command = typer.Typer()


@infra_command.command("apply")
@add_global_options
@cli_command
def apply_from_config(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Apply configuration to infrastructure and platform.
    """
    try:
        # Create execution context
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets, verbose=verbose)

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
@add_global_options
@cli_command
def destroy_all(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destruction"),
    force_delete_volumes: bool = typer.Option(
        False, "--force-delete-volumes", help="Delete volumes (PERMANENT DATA LOSS)"
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Destroy all infrastructure and platform resources.

    By default, Docker volumes (containing contest data) are PRESERVED.
    Use --force-delete-volumes to permanently delete all data.
    """
    if not confirm:
        typer.echo("❗ Use --confirm to actually destroy infrastructure.")
        typer.echo("   Containers will be stopped. Use --force-delete-volumes to also delete data.")
        raise typer.Exit(code=1)

    # Prompt for volume deletion BEFORE starting the spinner
    remove_volumes = force_delete_volumes
    if not force_delete_volumes:
        console.print("\n[yellow]⚠️  Volume Preservation Notice[/yellow]")
        console.print(
            "Docker volumes (containing contest data, database) will be [green]PRESERVED[/green] by default."
        )
        console.print(
            "To completely remove all data, use the [cyan]--force-delete-volumes[/cyan] flag."
        )
        console.print()

        # Ask if they want to delete anyway
        delete_confirm = Confirm.ask(
            "[red]Do you want to DELETE ALL VOLUMES? (This is PERMANENT and CANNOT be undone)[/red]",
            default=False,
            console=console,
        )
        remove_volumes = delete_confirm

    if remove_volumes:
        console.print(
            "\n[red]⚠️  WARNING: DELETING ALL VOLUMES - THIS WILL PERMANENTLY DELETE ALL CONTEST DATA![/red]\n"
        )

    try:
        # Create execution context
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets, verbose=verbose)

        # Destroy infrastructure with volume option
        runner = OperationRunner(DestroyInfrastructureOperation(remove_volumes))
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
@add_global_options
@cli_command
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
    try:
        # Load config if provided (to know expected judgehost count)
        config = None
        if file:
            load_runner = OperationRunner(LoadInfraConfigOperation(file), show_progress=False)
            secrets = get_secrets_manager()
            context = OperationContext(secrets=secrets, verbose=verbose)
            load_result = load_runner.run(context)

            if load_result.is_success():
                config = load_result.unwrap()

        # Check and print infrastructure status
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets, verbose=verbose)

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
