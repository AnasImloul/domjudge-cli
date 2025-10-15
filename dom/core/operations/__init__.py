"""Declarative operation framework for DomJudge CLI.

This module provides a declarative way to define and execute operations
with consistent error handling, logging, and validation.
"""

from .base import Operation, OperationContext, OperationResult
from .builders import OperationBuilder
from .runner import OperationRunner

__all__ = [
    "Operation",
    "OperationBuilder",
    "OperationContext",
    "OperationResult",
    "OperationRunner",
]
