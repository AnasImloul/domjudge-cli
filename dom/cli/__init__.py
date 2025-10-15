"""Main CLI entry point for DOMjudge CLI."""

from pathlib import Path

import typer

from dom.cli.contest import contest_command
from dom.cli.infra import infra_command
from dom.cli.init import init_command
from dom.logging_config import console, setup_logging
from dom.utils.cli import ensure_dom_directory

app = typer.Typer(help="dom-cli: Manage DOMjudge infrastructure and contests.")

# Register commands
app.add_typer(infra_command, name="infra", help="Manage infrastructure & platform")
app.add_typer(contest_command, name="contest", help="Manage contests")
app.add_typer(init_command, name="init", help="Initialize DOMjudge configuration files")


def main() -> None:
    """Main entry point with logging initialization."""
    # Initialize logging
    log_dir = ensure_dom_directory()
    log_file = log_dir / "domjudge-cli.log"
    setup_logging(level="INFO", log_file=log_file, enable_rich=True)

    # Run the CLI
    app()
