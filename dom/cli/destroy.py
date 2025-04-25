import typer
from dom.core.services.destroy import destroy_infra_and_platform

destroy_command = typer.Typer()


@destroy_command.command("destroy")
def destroy_all(
        confirm: bool = typer.Option(False, "--confirm", help="Confirm destruction")
) -> None:
    """
    Destroy all infrastructure and platform resources.
    """
    if not confirm:
        typer.echo("❗ Use --confirm to actually destroy.")
        raise typer.Exit(code=1)

    destroy_infra_and_platform()
