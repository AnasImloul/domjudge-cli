"""Decorators applied to every Typer CLI command.

These belong to the CLI layer (presentation): they configure logging,
catch errors, and render user-visible messages via ``dom.ui``. They
were previously in ``dom.utils.project`` — moved here so utilities stay
free of UI concerns.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import typer

from dom import ui
from dom.exceptions import DomJudgeCliError
from dom.logging_config import get_logger, setup_logging
from dom.utils.project import ensure_dom_directory

logger = get_logger(__name__)

T = TypeVar("T")


def add_global_options(func: Callable[..., T]) -> Callable[..., T]:
    """Adds ``--verbose`` / ``--no-color`` to a command and configures logging."""

    @wraps(func)
    def wrapper(
        *args,
        verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging output"),
        no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
        **kwargs,
    ) -> T:
        log_dir = ensure_dom_directory()
        log_file = log_dir / "domjudge-cli.log"
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(
            level=log_level,
            log_file=log_file,
            enable_rich=not no_color,
            console_output=verbose,
        )
        return func(*args, verbose=verbose, no_color=no_color, **kwargs)

    return wrapper


def cli_command(func: Callable[..., T]) -> Callable[..., T]:
    """Standard error handling and exit-code mapping for CLI commands."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except DomJudgeCliError as e:
            logger.error(f"Command failed: {e}")
            raise typer.Exit(code=1) from e
        except KeyboardInterrupt:
            logger.info("Command interrupted by user")
            ui.blank()
            ui.warn("** Operation cancelled by user")
            raise typer.Exit(code=130) from None
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            ui.error(f"x Unexpected error: {e}")
            ui.hint("Check logs at .dom/domjudge-cli.log for details")
            raise typer.Exit(code=1) from e

    return wrapper
