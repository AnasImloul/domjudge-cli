"""Init command implementation."""

import typer

from dom import ui
from dom.cli.init.wizard import run_wizard
from dom.logging_config import get_logger
from dom.utils.cli import add_global_options, cli_command

logger = get_logger(__name__)


@add_global_options
@cli_command
def callback(
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what files would be created without actually creating them",
    ),
    verbose: bool = False,  # noqa: ARG001
    no_color: bool = False,  # noqa: ARG001
):
    """
    Initialize the DOMjudge configuration files with an interactive wizard.

    Use --dry-run to preview what files would be created without actually creating them.
    """
    if dry_run:
        ui.write(
            "[yellow]* Dry run:[/yellow] would launch the interactive init wizard "
            "to create dom-judge.yaml (and optionally problems.yaml)."
        )
        return

    try:
        run_wizard(overwrite=overwrite)
    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Failed to initialize project: {e}", exc_info=True)
        ui.error(f"x Failed to initialize project: {e}")
        raise typer.Exit(code=1) from e
