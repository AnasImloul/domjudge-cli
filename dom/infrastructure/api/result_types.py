"""Standard result types for API operations.

This module provides consistent result objects for API operations,
making it easier for consumers to understand what to expect.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CreateResult:
    """
    Result of a create operation.

    Provides consistent information about whether a resource was created
    or already existed.

    Attributes:
        id: Identifier of the created or existing resource
        created: True if resource was newly created, False if it already existed
        data: Optional additional data about the resource
    """

    id: str
    created: bool
    data: Any | None = None

    def __bool__(self) -> bool:
        """Allow truthiness check on result (always True if we have an ID)."""
        return bool(self.id)


@dataclass
class OperationResult:
    """
    Generic result of an operation.

    Attributes:
        success: Whether the operation succeeded
        message: Optional message describing the result
        data: Optional data returned by the operation
    """

    success: bool
    message: str | None = None
    data: Any | None = None
