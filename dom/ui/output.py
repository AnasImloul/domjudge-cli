"""Console output helpers.

Each helper is a thin convenience around ``console.print``. Callers specialize
appearance via keyword arguments (``style``, ``spacer``, ...) rather than
embedding rich markup in every call site.
"""

from typing import Any

from dom.ui.console import console


def write(message: str = "", *, style: str | None = None) -> None:
    """Print a styled line. Pass ``style`` (e.g. ``"bold cyan"``) to colorize."""
    console.print(f"[{style}]{message}[/{style}]" if style else message)


def render(renderable: Any) -> None:
    """Print a rich renderable (Table, Panel, Progress, etc.) directly."""
    console.print(renderable)


def blank() -> None:
    """Emit a blank line."""
    console.print()


def header(title: str, *, style: str = "bold cyan", spacer: bool = True) -> None:
    """Print a section heading, optionally preceded by a blank line."""
    if spacer:
        console.print()
    console.print(f"[{style}]{title}[/{style}]")


def info(message: str) -> None:
    write(message)


def hint(message: str) -> None:
    write(message, style="dim")


def success(message: str, *, style: str = "green") -> None:
    write(message, style=style)


def warn(message: str, *, style: str = "yellow") -> None:
    write(message, style=style)


def error(message: str, *, style: str = "red") -> None:
    write(message, style=style)
