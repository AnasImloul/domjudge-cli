import typer
from dom.core.config.loaders import load_infrastructure_config
from dom.core.services.infra.apply import apply_infra_and_platform
from dom.core.services.infra.destroy import destroy_infra_and_platform

infra_command = typer.Typer()

@infra_command.command("apply")
def apply_from_config(
    file: str = typer.Option(None, "-f", "--file", help="Path to configuration YAML file")
) -> None:
    """
    Apply configuration to infrastructure and platform.
    """
    config = load_infrastructure_config(file)
    apply_infra_and_platform(config)



@infra_command.command("destroy")
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
