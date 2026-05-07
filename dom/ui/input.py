"""Interactive prompt helpers.

Wraps :mod:`rich.prompt` so callers don't import rich directly. Specialize
behavior with keyword arguments (``parser``, ``default``, ``password``,
``choices``, ``normalizer``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar, overload

from rich.prompt import Confirm, Prompt

from dom.ui.console import console
from dom.ui.output import error
from dom.utils.validators import Invalid

T = TypeVar("T")


@overload
def ask(
    message: str,
    *,
    default: str | None = ...,
    parser: Callable[[str], T],
    password: bool = ...,
    show_default: bool = ...,
) -> T: ...


@overload
def ask(
    message: str,
    *,
    default: str | None = ...,
    parser: None = ...,
    password: bool = ...,
    show_default: bool = ...,
) -> str: ...


def ask(
    message: str,
    *,
    default: str | None = None,
    parser: Callable[[str], T] | None = None,
    password: bool = False,
    show_default: bool = True,
) -> T | str:
    """Prompt for a value; reprompts on parser failure."""
    while True:
        raw = Prompt.ask(
            message,
            default=default or "",
            show_default=show_default,
            password=password,
            console=console,
        )
        try:
            return parser(raw) if parser else raw
        except Invalid as e:
            error(str(e))
        except Exception as e:
            error(str(e))
            error("Invalid value.")


def ask_bool(message: str, *, default: bool = True) -> bool:
    """Prompt for a yes/no answer."""
    return Confirm.ask(message, default=default, console=console)


def ask_choice(
    message: str,
    *,
    choices: Iterable[str],
    default: str | None = None,
    normalizer: Callable[[str], str] | None = None,
    show_default: bool = True,
) -> str:
    """Prompt for one of a fixed set of string choices.

    If ``normalizer`` is supplied, both user input and the choice list are
    normalized for matching, but the original (un-normalized) value is returned.
    """
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
