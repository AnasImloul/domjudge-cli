"""Contest CLI commands."""

import typer

from dom.cli.contest.apply import apply_command
from dom.cli.contest.inspect import inspect_command
from dom.cli.contest.plan import plan_command
from dom.cli.contest.verify_problemset import verify_problemset_command
from dom.logging_config import get_logger

logger = get_logger(__name__)
contest_command = typer.Typer()

# Register commands
contest_command.command("apply")(apply_command)
contest_command.command("plan")(plan_command)
contest_command.command("verify-problemset")(verify_problemset_command)
contest_command.command("inspect")(inspect_command)

__all__ = ["contest_command"]
