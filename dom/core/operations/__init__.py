"""Declarative operations framework for DomJudge CLI.

See :mod:`dom.core.operations.framework` for the framework, and
:mod:`dom.core.operations.contest` / :mod:`dom.core.operations.infrastructure`
for concrete operations.
"""

from . import contest, infrastructure
from .framework import Context, Operation, Step, Steps, operation, run

__all__ = [
    "Context",
    "Operation",
    "Step",
    "Steps",
    "contest",
    "infrastructure",
    "operation",
    "run",
]
