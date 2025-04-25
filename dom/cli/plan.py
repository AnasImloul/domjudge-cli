import typer
from dom.infrastructure.config_loader import load_config
from dom.core.services.plan import plan_infra_and_platform

plan_command = typer.Typer()

@plan_command.command("plan")
def plan_from_config(
    file: str = typer.Option(..., "-f", "--file", help="Path to configuration YAML file")
) -> None:
    """
    Show what would change if applying the configuration.
    """
    config = load_config(file)
    plan_infra_and_platform(config)
