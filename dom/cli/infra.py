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
    try:
        # Create execution context
        secrets = get_secrets_manager()

        # Load configuration (always runs, even in dry-run mode, since it's read-only)
        load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
        load_runner = OperationRunner(LoadInfraConfigOperation(file))
        load_result = load_runner.run(load_context)

        if not load_result.is_success():
            raise typer.Exit(code=1)

        config = load_result.unwrap()

        if dry_run:
            # Display dry-run preview
            console.print("\n[bold cyan]DRY RUN - Preview Mode[/bold cyan]\n")
            console.print("[dim]No changes will be made to the infrastructure[/dim]\n")
            console.print("[yellow]Would deploy:[/yellow]")
            console.print(f"  - DOMserver on port {config.port}")
            console.print("  - MariaDB database")
            console.print(f"  - {config.judges} judgehost(s)")
            console.print("  - MySQL client container")
            console.print()
            console.print("[yellow]Would configure:[/yellow]")
            console.print("  - Admin password (from secrets)")
            console.print("  - Database password (auto-generated)")
            console.print("  - Judgedaemon authentication")
            console.print()
            console.print("[green]+[/green] To actually apply, run without --dry-run")
            console.print("[dim]  Example: dom infra apply[/dim]")
            return

        # Apply infrastructure with actual context
        apply_context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)
        apply_runner = OperationRunner(ApplyInfrastructureOperation(config))
        apply_result = apply_runner.run(apply_context)

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
    if dry_run:
        console.print("\n[bold cyan]DRY RUN - Preview Mode[/bold cyan]\n")
        console.print("[dim]No changes will be made to the infrastructure[/dim]\n")
        console.print("[yellow]Would destroy:[/yellow]")
        console.print("  - All DOMjudge containers (domserver, judgehosts, mariadb, mysql-client)")
        if force_delete_volumes:
            console.print("  - [red]All Docker volumes (PERMANENT DATA LOSS)[/red]")
        else:
            console.print("  - [green]Volumes would be PRESERVED[/green]")
        console.print()
        console.print("[green]+[/green] To actually destroy, run without --dry-run")
        console.print("[dim]  Example: dom infra destroy --confirm --force-delete-volumes[/dim]")
        return

    if not confirm:
        typer.echo("! Use --confirm to actually destroy infrastructure.")
        typer.echo("   Containers will be stopped. Use --force-delete-volumes to also delete data.")
        raise typer.Exit(code=1)

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

    try:
        # Create execution context
        secrets = get_secrets_manager()
        context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)

        # Destroy infrastructure with volume option
        runner = OperationRunner(DestroyInfrastructureOperation(force_delete_volumes))
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
