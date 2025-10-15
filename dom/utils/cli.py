from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import TypeVar

import typer
from rich.prompt import Confirm

from dom.exceptions import DomJudgeCliError
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import console, get_logger

logger = get_logger(__name__)

# Type variable for generic decorator
T = TypeVar("T")


def ensure_dom_directory() -> Path:
    """
    Ensure that the .dom directory exists in the current working directory.
    Returns the absolute path to the .dom folder.
    """
    dom_path = Path.cwd() / ".dom"
    dom_path.mkdir(exist_ok=True)
    return dom_path


def get_secrets_manager() -> SecretsManager:
    """
    Get initialized secrets manager for the current project.

    Returns:
        Configured SecretsManager instance
    """
    return SecretsManager(ensure_dom_directory())


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
            console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
            raise typer.Exit(code=130) from None
        except Exception as e:
            # Unexpected errors - log with full traceback
            logger.error(f"Unexpected error: {e}", exc_info=True)
            console.print(f"[red]✗ Unexpected error: {e}[/red]")
            console.print("[dim]Check logs at .dom/domjudge-cli.log for details[/dim]")
            raise typer.Exit(code=1) from e

    return wrapper


def find_config_or_default(file: Path | None) -> Path:
    """
    Find configuration file or use default.

    Args:
        file: Optional explicit config file path

    Returns:
        Path to configuration file

    Raises:
        FileNotFoundError: If config file not found
        FileExistsError: If both .yaml and .yml exist
    """
    if file:
        if not file.is_file():
            raise FileNotFoundError(f"Specified config file '{file}' not found.")
        return file

    yaml_path = Path("dom-judge.yaml")
    yml_path = Path("dom-judge.yml")

    if yaml_path.is_file() and yml_path.is_file():
        raise FileExistsError(
            "Both 'dom-judge.yaml' and 'dom-judge.yml' exist. "
            "Please specify which one to use with --file."
        )
    if not yaml_path.is_file() and not yml_path.is_file():
        raise FileNotFoundError(
            "No 'dom-judge.yaml' or 'dom-judge.yml' found. "
            "Please specify a config file with --file or run 'dom init' first."
        )

    return yaml_path if yaml_path.is_file() else yml_path


def check_file_exists(file: Path) -> bool:
    """
    Check if file exists and raise error if it does.

    Args:
        file: File path to check

    Returns:
        False (file doesn't exist)

    Raises:
        FileExistsError: If file exists
    """
    if file.is_file():
        raise FileExistsError(
            f"File '{file}' already exists. "
            "Rename or remove the existing file, or use --overwrite to replace it."
        )
    return False


def ask_override_if_exists(output_file: Path) -> bool:
    """
    Ask user whether to override if the output file exists.

    Args:
        output_file: Path to check

    Returns:
        True if should proceed, False if should skip
    """
    if output_file.exists():
        override = Confirm.ask(
            f"File '{output_file}' exists. Do you want to override it?",
            default=False,
            console=console,
        )
        if not override:
            console.print("[yellow]Skipping problem initialization.[/yellow]")
            return False
    return True
