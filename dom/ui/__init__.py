"""Owner module for all user-facing console interaction.

Public facade. Every other module in the codebase reads from / writes to the
user through the names re-exported here. Callers should not import
``rich.console``, ``rich.prompt``, or instantiate their own ``Console``.

Submodules:
    console — single shared rich Console instance
    output  — write / render / header / info / hint / success / warn / error
    input   — ask / ask_bool / ask_choice
"""

from dom.ui.console import console
from dom.ui.input import ask, ask_bool, ask_choice
from dom.ui.output import (
    blank,
    error,
    header,
    hint,
    info,
    render,
    success,
    warn,
    write,
)

__all__ = [
    "ask",
    "ask_bool",
    "ask_choice",
    "blank",
    "console",
    "error",
    "header",
    "hint",
    "info",
    "render",
    "success",
    "warn",
    "write",
]
