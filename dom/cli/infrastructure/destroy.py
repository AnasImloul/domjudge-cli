"""Infrastructure destroy command."""

import typer

from dom.cli.helpers import add_global_options, cli_command, get_secrets_manager
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import DestroyInfrastructureOperation
from dom.logging_config import console


@add_global_options
@cli_command
def destroy_command(
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
