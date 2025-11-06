"""Init CLI command."""

import typer

from dom.cli.init.command import callback
from dom.logging_config import get_logger

logger = get_logger(__name__)
init_command = typer.Typer()

init_command.callback(invoke_without_command=True)(callback)

__all__ = ["init_command"]
