"""Declarative operations framework for DomJudge CLI.

See :mod:`dom.core.operations.framework` for the framework, and
:mod:`dom.core.operations.contest` / :mod:`dom.core.operations.infrastructure`
for concrete operations.
"""

from . import contest, infrastructure
from .framework import (
    Context,
    Operation,
    Renderer,
    Step,
    StepProgress,
    Steps,
    operation,
    run,
    set_default_renderer,
)

__all__ = [
    "Context",
    "Operation",
    "Renderer",
    "Step",
    "StepProgress",
    "Steps",
    "contest",
    "infrastructure",
    "operation",
    "run",
    "set_default_renderer",
]
