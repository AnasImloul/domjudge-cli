"""Infrastructure destroy command."""

import typer

from dom import ui
from dom.cli.decorators import add_global_options, cli_command
from dom.core.operations import Context, run
from dom.core.operations.infrastructure import destroy_infrastructure_op
from dom.utils.cli import get_secrets_manager


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
    """Destroy all infrastructure and platform resources.

    By default Docker volumes (containing contest data) are PRESERVED.
    Use ``--force-delete-volumes`` to permanently delete all data.
    """
    if not dry_run and not confirm:
        ui.warn("Use --confirm to actually destroy infrastructure.")
        ui.write("   Containers will be stopped. Use --force-delete-volumes to also delete data.")
        raise typer.Exit(code=1)

    if not dry_run:
        if not force_delete_volumes:
            ui.header("** Volume Preservation Notice", style="yellow")
            ui.write(
                "Docker volumes (containing contest data, database) will be"
                " [green]PRESERVED[/green] by default."
            )
            ui.write(
                "To completely remove all data, use the [cyan]--force-delete-volumes[/cyan] flag."
            )
            ui.blank()
        else:
            ui.blank()
            ui.error(
                "** WARNING: DELETING ALL VOLUMES - "
                "THIS WILL PERMANENTLY DELETE ALL CONTEST DATA!"
            )
            ui.blank()

    secrets = get_secrets_manager()
    run(
        destroy_infrastructure_op(force_delete_volumes),
        Context(secrets=secrets, dry_run=dry_run, verbose=verbose),
    )
