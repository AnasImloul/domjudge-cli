import typer
from dom.infrastructure.config_loader import load_config
from dom.core.services.apply import apply_infra_and_platform

apply_command = typer.Typer()

@apply_command.command("apply")
def apply_from_config(
    file: str = typer.Option(..., "-f", "--file", help="Path to configuration YAML file")
) -> None:
    """
    Apply configuration to infra and platform.
    """
    config = load_config(file)
    apply_infra_and_platform(config)
