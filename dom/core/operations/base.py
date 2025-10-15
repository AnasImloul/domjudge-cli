"""Base operation types for declarative operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from dom.logging_config import get_logger
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)

T = TypeVar("T")


class OperationStatus(str, Enum):
    """Status of an operation execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class OperationContext:
    """
    Context for operation execution.

    Provides dependencies and configuration needed by operations.
    Immutable after construction for predictable behavior.

    Note: Uses SecretsProvider interface rather than concrete implementation,
    following Dependency Inversion Principle.
    """

    secrets: SecretsProvider
    dry_run: bool = False
    verbose: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **kwargs: Any) -> "OperationContext":
        """Create new context with additional metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return OperationContext(
            secrets=self.secrets,
            dry_run=self.dry_run,
            verbose=self.verbose,
            metadata=new_metadata,
        )


@dataclass
class OperationResult(Generic[T]):
    """
    Result of an operation execution.

    Encapsulates success/failure state with optional data or error information.
    """

    status: OperationStatus
    data: T | None = None
    error: Exception | None = None
    message: str = ""

    @classmethod
    def success(cls, data: T | None = None, message: str = "") -> "OperationResult[T]":
        """Create a successful result."""
        return cls(status=OperationStatus.SUCCESS, data=data, message=message)

    @classmethod
    def failure(cls, error: Exception, message: str = "") -> "OperationResult[T]":
        """Create a failed result."""
        return cls(status=OperationStatus.FAILURE, error=error, message=message)

    @classmethod
    def skipped(cls, message: str = "") -> "OperationResult[T]":
        """Create a skipped result."""
        return cls(status=OperationStatus.SKIPPED, message=message)

    def is_success(self) -> bool:
        """Check if operation was successful."""
        return self.status == OperationStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if operation failed."""
        return self.status == OperationStatus.FAILURE

    def unwrap(self) -> T:
        """
        Get the result data or raise the error.

        Raises:
            ValueError: If result has no data
            Exception: If result contains an error
        """
        if self.error:
            raise self.error
        if self.data is None:
            raise ValueError(f"Operation result has no data: {self.message}")
        return self.data


class Operation(ABC, Generic[T]):
    """
    Base class for declarative operations.

    Operations encapsulate a single unit of work with clear inputs,
    outputs, and error handling. They follow these principles:

    1. Single Responsibility: Each operation does one thing
    2. Declarative: Operations declare what they do, not how
    3. Composable: Operations can be combined to build workflows
    4. Testable: Easy to test in isolation
    5. Immutable: Operations don't modify external state unexpectedly

    Example:
        >>> class LoadConfigOperation(Operation[DomConfig]):
        ...     def describe(self) -> str:
        ...         return "Load DomJudge configuration"
        ...
        ...     def validate(self, context: OperationContext) -> list[str]:
        ...         if not self.config_path.exists():
        ...             return [f"Config file not found: {self.config_path}"]
        ...         return []
        ...
        ...     def execute(self, context: OperationContext) -> OperationResult[DomConfig]:
        ...         config = load_config(self.config_path, context.secrets)
        ...         return OperationResult.success(config, "Configuration loaded")
    """

    @abstractmethod
    def describe(self) -> str:
        """
        Return a human-readable description of what this operation does.

        This should be written in declarative form, describing the intent
        rather than implementation details.

        Returns:
            Description of the operation
        """

    def validate(self, context: OperationContext) -> list[str]:  # noqa: ARG002
        """
        Validate that the operation can be executed.

        Returns:
            List of validation errors (empty if valid)
        """
        return []

    @abstractmethod
    def execute(self, context: OperationContext) -> OperationResult[T]:
        """
        Execute the operation.

        Args:
            context: Execution context with dependencies

        Returns:
            Result of the operation
        """

    def __str__(self) -> str:
        """String representation for logging."""
        return self.describe()
