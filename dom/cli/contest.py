import typer
from dom.infrastructure.config import load_config
from dom.core.services.contest.apply import apply_contests

contest_command = typer.Typer()

@contest_command.command("apply")
def apply_from_config(
    file: str = typer.Option(None, "-f", "--file", help="Path to configuration YAML file")
) -> None:
    """
    Apply configuration to contests in the platform.
    """
    config = load_config(file)
    apply_contests(config)
