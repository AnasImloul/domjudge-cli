from pathlib import Path

import typer

from dom.cli.validators import validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import (
    ApplyInfrastructureOperation,
    DestroyInfrastructureOperation,
    LoadInfraConfigOperation,
    PlanInfraChangesOperation,
    PrintInfrastructureStatusOperation,
)
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
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Apply configuration to infrastructure and platform.

    Use --dry-run to preview what changes would be made without actually applying them.
    """
    # Create execution context
    secrets = get_secrets_manager()

    # Load configuration (always runs, even in dry-run mode, since it's read-only)
    load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    load_runner = OperationRunner(LoadInfraConfigOperation(file))
    load_result = load_runner.run(load_context)

    if not load_result.is_success():
        raise typer.Exit(code=1)

    config = load_result.unwrap()

    # Apply infrastructure with context (operations handle dry-run)
    apply_context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)
    apply_runner = OperationRunner(ApplyInfrastructureOperation(config))
    apply_result = apply_runner.run(apply_context)

    # Don't treat dry-run (skipped) as failure
    if apply_result.is_failure():
        raise typer.Exit(code=1)


@infra_command.command("plan")
@add_global_options
@cli_command
def plan_changes(
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
    # Create execution context
    secrets = get_secrets_manager()

    # Load configuration
    load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    load_runner = OperationRunner(LoadInfraConfigOperation(file))
    load_result = load_runner.run(load_context)

    if not load_result.is_success():
        raise typer.Exit(code=1)

    config = load_result.unwrap()

    # Plan changes
    plan_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    plan_runner = OperationRunner(PlanInfraChangesOperation(config), show_progress=False)
    plan_result = plan_runner.run(plan_context)

    if plan_result.is_failure():
        raise typer.Exit(code=1)


@infra_command.command("destroy")
@add_global_options
@cli_command
def destroy_all(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destruction"),
    force_delete_volumes: bool = typer.Option(
        False, "--force-delete-volumes", help="Delete volumes (PERMANENT DATA LOSS)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview what would be destroyed without actually destroying"
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Destroy all infrastructure and platform resources.

    By default, Docker volumes (containing contest data) are PRESERVED.
    Use --force-delete-volumes to permanently delete all data.
    Use --dry-run to preview what would be destroyed without actually destroying.
    """
    # Validation: require confirmation unless in dry-run mode
    if not dry_run and not confirm:
        typer.echo("! Use --confirm to actually destroy infrastructure.")
        typer.echo("   Containers will be stopped. Use --force-delete-volumes to also delete data.")
        raise typer.Exit(code=1)

    # Display warnings before destruction
    if not dry_run:
        if not force_delete_volumes:
            console.print("\n[yellow]** Volume Preservation Notice[/yellow]")
            console.print(
                "Docker volumes (containing contest data, database) will be [green]PRESERVED[/green] by default."
            )
            console.print(
                "To completely remove all data, use the [cyan]--force-delete-volumes[/cyan] flag."
            )
            console.print()

        if force_delete_volumes:
            console.print(
                "\n[red]** WARNING: DELETING ALL VOLUMES - THIS WILL PERMANENTLY DELETE ALL CONTEST DATA![/red]\n"
            )

    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)

    # Destroy infrastructure with volume option (operations handle dry-run)
    runner = OperationRunner(DestroyInfrastructureOperation(force_delete_volumes))
    result = runner.run(context)

    # Don't treat dry-run (skipped) as failure
    if result.is_failure():
        raise typer.Exit(code=1)


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
