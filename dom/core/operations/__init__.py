"""Declarative operation framework for DomJudge CLI.

This module provides a declarative way to define and execute operations
with consistent error handling, logging, and validation.
"""

# Core abstractions
# Operations by domain
from . import contest, infrastructure
from .base import (
    ExecutableStep,
    Operation,
    OperationContext,
    OperationResult,
    SimpleOperation,
    SteppedOperation,
)
from .runner import OperationRunner

__all__ = [
    # Core abstractions
    "ExecutableStep",
    "Operation",
    "OperationContext",
    "OperationResult",
    "OperationRunner",
    "SimpleOperation",
    "SteppedOperation",
    # Domain modules
    "contest",
    "infrastructure",
]
