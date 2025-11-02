"""Base operation types for declarative operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from dom.logging_config import get_logger
from dom.types.secrets import SecretsProvider

if TYPE_CHECKING:
    from typing import Any

logger = get_logger(__name__)

T = TypeVar("T")


class OperationStatus(str, Enum):
    """Status of an operation execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class OperationStep:
    """
    Represents a single step in an operation.

    Steps allow operations to declare their work upfront, enabling:
    - Better progress tracking
    - Step-by-step execution
    - Clear visibility into operation phases
    - Easier testing and debugging
    """

    name: str
    description: str
    weight: float = 1.0  # Relative weight for progress calculation

    def __str__(self) -> str:
        """String representation for display."""
        return self.description


class ExecutableStep(ABC):
    """
    Base class for executable operation steps.

    Each step is a self-contained unit of work with its own execution logic.
    This follows the Command pattern, making steps reusable and testable.

    Example:
        >>> class LoadConfigStep(ExecutableStep):
        ...     def __init__(self, config_path: Path):
        ...         super().__init__("load", "Load configuration file")
        ...         self.config_path = config_path
        ...
        ...     def execute(self, context: OperationContext) -> Any:
        ...         return load_config(self.config_path)
    """

    def __init__(self, name: str, description: str, weight: float = 1.0):
        """
        Initialize an executable step.

        Args:
            name: Unique identifier for the step
            description: Human-readable description
            weight: Relative weight for progress calculation
        """
        self.name = name
        self.description = description
        self.weight = weight

    @abstractmethod
    def execute(self, context: OperationContext) -> Any:
        """
        Execute this step.

        Args:
            context: Execution context with dependencies

        Returns:
            Step result (can be any type)

        Raises:
            Exception: If step execution fails
        """

    def should_execute(self, _context: OperationContext) -> bool:
        """
        Determine if this step should be executed.

        Override this to implement conditional step execution.
        Default implementation returns True (always execute).

        Args:
            context: Execution context

        Returns:
            True if step should be executed, False to skip
        """
        return True

    def to_operation_step(self) -> OperationStep:
        """Convert to OperationStep for compatibility."""
        return OperationStep(self.name, self.description, self.weight)

    def __str__(self) -> str:
        """String representation for display."""
        return self.description


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

    def with_metadata(self, **kwargs: Any) -> OperationContext:
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
    def success(cls, data: T | None = None, message: str = "") -> OperationResult[T]:
        """Create a successful result."""
        return cls(status=OperationStatus.SUCCESS, data=data, message=message)

    @classmethod
    def failure(cls, error: Exception, message: str = "") -> OperationResult[T]:
        """Create a failed result."""
        return cls(status=OperationStatus.FAILURE, error=error, message=message)

    @classmethod
    def skipped(cls, message: str = "") -> OperationResult[T]:
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

    def validate(self, _context: OperationContext) -> list[str]:
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


class SteppedOperation(Operation[T], ABC):
    """
    Operation that declares its execution steps upfront.

    This provides better user experience by:
    - Showing what steps will be performed before execution
    - Tracking progress through each step
    - Making the operation more transparent and predictable

    Subclasses must implement:
    - define_steps(): Return list of ExecutableStep instances

    The base execute() method is implemented to:
    - Iterate through all defined steps
    - Track step progress
    - Handle step errors
    - Accumulate step results

    Example:
        >>> class DeployInfraOperation(SteppedOperation[None]):
        ...     def describe(self) -> str:
        ...         return "Deploy infrastructure"
        ...
        ...     def define_steps(self) -> list[ExecutableStep]:
        ...         return [
        ...             ValidatePrerequisitesStep(),
        ...             GenerateComposeStep(self.config),
        ...             StartContainersStep(self.config),
        ...         ]
    """

    @abstractmethod
    def define_steps(self) -> list[ExecutableStep]:
        """
        Define the steps this operation will perform.

        Steps are executed in order. Each step should represent a
        meaningful unit of work that can be tracked independently.

        Returns:
            List of executable steps
        """

    def execute(self, context: OperationContext) -> OperationResult[T]:
        """
        Execute all steps in sequence.

        This method is implemented by SteppedOperation and should not
        be overridden. Instead, implement individual ExecutableStep classes.

        Args:
            context: Execution context

        Returns:
            Operation result
        """
        steps = self.define_steps()
        step_results: dict[str, Any] = {}

        try:
            for step in steps:
                # Check if step should be executed
                if not step.should_execute(context):
                    logger.info(f"Skipping step: {step.name}")
                    continue

                # Execute the step
                result = step.execute(context)
                step_results[step.name] = result

            # Build final result from step results
            final_result = self._build_result(step_results, context)
            return final_result

        except Exception as e:
            logger.error(
                f"Step execution failed in {self.describe()}",
                exc_info=True,
                extra={"operation": self.describe()},
            )
            return OperationResult.failure(e, f"Step execution failed: {e}")

    def _build_result(
        self,
        _step_results: dict[str, Any],
        _context: OperationContext,
    ) -> OperationResult[T]:
        """
        Build final operation result from step results.

        Default implementation returns success with None data.
        Override this to customize result building.

        Args:
            step_results: Dictionary mapping step names to their results
            context: Execution context

        Returns:
            Final operation result
        """
        return OperationResult.success(None, f"{self.describe()} completed successfully")
