from collections.abc import Callable
from functools import wraps
from hashlib import sha256
from pathlib import Path
from typing import TypeVar

import typer
from rich.prompt import Confirm

from dom.exceptions import DomJudgeCliError
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import console, get_logger, setup_logging

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


def get_container_prefix() -> str:
    """
    Generate a unique container prefix based on the current working directory.

    This allows multiple DOMjudge instances to run simultaneously from different
    directories without naming collisions. The prefix is generated from a hash
    of the absolute path to ensure it's deterministic and filesystem-safe.

    Returns:
        A container prefix like 'domjudge-abc123' based on the directory path

    Example:
        >>> # In /home/user/contest1:
        >>> get_container_prefix()
        'domjudge-a3f4b2'
        >>> # In /home/user/contest2:
        >>> get_container_prefix()
        'domjudge-c7e891'
    """
    # Get absolute path of current working directory
    cwd = Path.cwd().resolve()

    # Generate a short hash from the path (first 6 chars of SHA256)
    path_hash = sha256(str(cwd).encode()).hexdigest()[:6]

    return f"domjudge-{path_hash}"


def get_secrets_manager() -> SecretsManager:
    """
    Get initialized secrets manager for the current project.

    Returns:
        Configured SecretsManager instance
    """
    return SecretsManager(ensure_dom_directory())


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


def find_file_with_extensions(
    base_path: Path | str,
    base_name: str,
    extensions: tuple[str, str] = (".yaml", ".yml"),
    error_context: str | None = None,
) -> Path:
    """
    Find a file with .yaml or .yml extension, with fallback support.

    This function abstracts the common pattern of looking for configuration files
    that can have either .yaml or .yml extensions. It handles:
    - Explicit file paths (returned as-is if they exist)
    - Directory paths (searches for base_name.yaml or base_name.yml within)
    - Base name only (searches in current directory)

    Args:
        base_path: Base path (file, directory, or relative name)
        base_name: Base name of the file (e.g., "dom-judge", "problems")
        extensions: Tuple of extensions to try (default: .yaml, .yml)
        error_context: Optional context for error messages

    Returns:
        Path to the found file

    Raises:
        FileNotFoundError: If no file found with any extension
        FileExistsError: If both .yaml and .yml exist
    """
    base_path = Path(base_path)

    # If base_path is an explicit file that exists, return it
    if base_path.is_file():
        return base_path

    # If base_path is a directory, search within it; otherwise use current directory
    search_dir = base_path if base_path.is_dir() else Path.cwd()

    # Try both extensions
    ext1, ext2 = extensions
    path1 = search_dir / f"{base_name}{ext1}"
    path2 = search_dir / f"{base_name}{ext2}"

    if path1.is_file() and path2.is_file():
        raise FileExistsError(
            f"Both '{path1.name}' and '{path2.name}' exist in '{search_dir}'. "
            f"Please specify which one to use explicitly."
        )

    if path1.is_file():
        return path1
    if path2.is_file():
        return path2

    # Nothing found
    raise FileNotFoundError(
        f"No '{base_name}{ext1}' or '{base_name}{ext2}' found in '{search_dir}'. "
        f"{error_context or ''}"
    )


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

    return find_file_with_extensions(
        base_path=Path.cwd(),
        base_name="dom-judge",
        error_context="Please specify a config file with --file or run 'dom init' first.",
    )


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
