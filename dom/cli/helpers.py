"""CLI-specific helper utilities for DOMjudge CLI commands.

This module provides CLI-specific utilities:
- CLI decorators for global options and error handling
- User interaction prompts
- CLI-specific error formatting

For generic file system utilities, use dom.shared.filesystem instead.
"""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

import typer

from dom.exceptions import DomJudgeCliError
from dom.logging_config import console, get_logger, setup_logging
from dom.shared.filesystem import ensure_dom_directory
from dom.shared.prompts import prompt_file_overwrite

logger = get_logger(__name__)

# Type variable for generic decorator
T = TypeVar("T")


def add_global_options(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that adds global CLI options to any command function.

    This decorator automatically adds the following global options:
    - --verbose: Enable verbose logging output
    - --no-color: Disable colored output

    The options are added as parameters to the function, so they can be used
    directly in the command implementation.

    Usage:
        @app.command()
        @add_global_options
        def my_command(arg: str, verbose: bool = False, no_color: bool = False):
            # Command logic here
            pass
    """

    @wraps(func)
    def wrapper(
        *args,
        verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging output"),
        no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
        **kwargs,
    ) -> T:
        # Configure logging for this command
        log_dir = ensure_dom_directory()
        log_file = log_dir / "domjudge-cli.log"
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(
            level=log_level, log_file=log_file, enable_rich=not no_color, console_output=verbose
        )

        return func(*args, verbose=verbose, no_color=no_color, **kwargs)

    return wrapper


def cli_command(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for CLI commands with consistent error handling and logging.

    This decorator:
    - Catches DomJudgeCliError and exits with code 1
    - Catches unexpected exceptions, logs them, and exits with code 1
    - Provides consistent error messaging across all commands

    Usage:
        @app.command()
        @cli_command
        def my_command(arg: str):
            # Command logic here
            pass

    Args:
        func: The CLI command function to wrap

    Returns:
        Wrapped function with error handling
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except DomJudgeCliError as e:
            # Expected application errors
            logger.error(f"Command failed: {e}")
            raise typer.Exit(code=1) from e
        except KeyboardInterrupt:
            # User interrupted
            logger.info("Command interrupted by user")
            console.print("\n[yellow]** Operation cancelled by user[/yellow]")
            raise typer.Exit(code=130) from None
        except Exception as e:
            # Unexpected errors - log with full traceback
            logger.error(f"Unexpected error: {e}", exc_info=True)
            console.print(f"[red]x Unexpected error: {e}[/red]")
            console.print("[dim]Check logs at .dom/domjudge-cli.log for details[/dim]")
            raise typer.Exit(code=1) from e

    return wrapper


def ask_override_if_exists(output_file: Path) -> bool:
    """
    Ask user whether to override if the output file exists.

    This is a CLI-specific wrapper around the shared prompt function.
    Prefer using dom.shared.prompts.prompt_file_overwrite for new code.

    Args:
        output_file: Path to check

    Returns:
        True if should proceed, False if should skip
    """
    return prompt_file_overwrite(output_file, "problem initialization")


# Re-export commonly used shared utilities for convenience
# This allows CLI code to import from one place while respecting layering
from dom.shared.filesystem import (  # noqa: E402
    check_file_exists,
    find_config_or_default,
    find_file_with_extensions,
    get_container_prefix,
    get_secrets_manager,
)

__all__ = [
    "add_global_options",
    "ask_override_if_exists",
    "check_file_exists",
    "cli_command",
    "ensure_dom_directory",
    "find_config_or_default",
    "find_file_with_extensions",
    "get_container_prefix",
    "get_secrets_manager",
]
