"""Infrastructure CLI commands."""

import typer

from dom.cli.infrastructure.apply import apply_command
from dom.cli.infrastructure.destroy import destroy_command
from dom.cli.infrastructure.plan import plan_command
from dom.cli.infrastructure.status import status_command
from dom.logging_config import get_logger

logger = get_logger(__name__)
infra_command = typer.Typer()

# Register commands
infra_command.command("apply")(apply_command)
infra_command.command("plan")(plan_command)
infra_command.command("destroy")(destroy_command)
infra_command.command("status")(status_command)

__all__ = ["infra_command"]
