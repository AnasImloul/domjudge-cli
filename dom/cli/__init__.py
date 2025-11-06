"""Main CLI entry point for DOMjudge CLI."""

import logging
from pathlib import Path

import typer

from dom import __version__
from dom.cli.contest import contest_command
from dom.cli.infrastructure import infra_command
from dom.cli.init import init_command
from dom.logging_config import console, get_logger, setup_logging
from dom.utils.cli import ensure_dom_directory

logger = get_logger(__name__)

app = typer.Typer(help="dom-cli: Manage DOMjudge infrastructure and contests.")

# Register commands
app.add_typer(infra_command, name="infra", help="Manage infrastructure & platform")
app.add_typer(contest_command, name="contest", help="Manage contests")
app.add_typer(init_command, name="init", help="Initialize DOMjudge configuration files")


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging output",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output",
    ),
) -> None:
    """Global options for the CLI."""
    # Initialize logging first (needed for verbose)
    log_dir = ensure_dom_directory()
    log_file = log_dir / "domjudge-cli.log"
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(
        level=log_level, log_file=log_file, enable_rich=not no_color, console_output=verbose
    )

    if verbose:
        logger.debug("Verbose logging enabled")
    if no_color:
        logger.debug("Color output disabled")

    # Handle version flag
    if version:
        console.print(f"dom-cli version {__version__}")
        raise typer.Exit()

    # Store verbose flag in context for subcommands
    ctx.obj = {"verbose": verbose}

    # If no subcommand was provided, show help
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


def main() -> None:
    """Main entry point."""
    app()
