from collections.abc import Callable, Iterable
from typing import TypeVar

from rich.console import Console
from rich.prompt import Confirm, Prompt

from dom.utils.validators import Invalid

T = TypeVar("T")


def ask(
    message: str,
    *,
    console: Console,
    default: str | None = None,
    parser: Callable[[str], T] | None = None,
    password: bool = False,
    show_default: bool = True,
) -> T | str:
    """Prompt once; parse; reprompt on error. All looping is hidden here."""
    while True:
        raw: str = Prompt.ask(
            message,
            default=default or "",
            show_default=show_default,
            password=password,
            console=console,
        )
        try:
            value: T | str = parser(raw) if parser else raw
            return value
        except Invalid as e:
            console.print(f"[red]{e}[/red]")
        except Exception as e:
            console.print(f"[red]{e}[/red]")
            console.print("[red]Invalid value.[/red]")


def ask_bool(message: str, *, console: Console, default: bool = True) -> bool:
    return Confirm.ask(message, default=default, console=console)


def ask_choice(
    message: str,
    *,
    console: Console,
    choices: Iterable[str],
    default: str | None = None,
    normalizer: Callable[[str], str] | None = None,
    show_default: bool = True,
) -> str:
    """Prompt with a fixed set of string choices; reprompts on invalid."""
    normalized = {(normalizer(c) if normalizer else c): c for c in choices}
    while True:
        raw = Prompt.ask(
            message,
            choices=list(normalized.keys()),
            default=default,
            show_default=show_default,
            console=console,
        )
        key = normalizer(raw) if normalizer and raw else raw
        if key in normalized:
            return normalized[key]
