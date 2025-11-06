"""Generic user prompts for file operations.

These are infrastructure-agnostic prompts that can be used by any layer.
"""

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

console = Console()


def prompt_file_overwrite(file_path: Path, action_description: str = "operation") -> bool:
    """
    Prompt user whether to overwrite an existing file.

    Args:
        file_path: Path to check
        action_description: Description of what will be skipped if user says no

    Returns:
        True if should proceed, False if should skip
    """
    if file_path.exists():
        override = Confirm.ask(
            f"File '{file_path}' exists. Do you want to override it?",
            default=False,
            console=console,
        )
        if not override:
            console.print(f"[yellow]Skipping {action_description}.[/yellow]")
            return False
    return True
