"""Builders for composing operations declaratively."""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

from dom.logging_config import get_logger

from .base import Operation, OperationContext, OperationResult

logger = get_logger(__name__)

T = TypeVar("T")
U = TypeVar("U")


class OperationBuilder(Generic[T]):
    """
    Builder for composing operations in a declarative way.

    This allows building complex workflows by chaining operations
    with transformations and error handling.

    Example:
        >>> builder = (
        ...     OperationBuilder(LoadConfigOperation(path))
        ...     .then(ValidateConfigOperation())
        ...     .then(ApplyConfigOperation())
        ...     .on_error(lambda e: logger.error(f"Failed: {e}"))
        ... )
        >>> result = builder.run(context)
    """

    def __init__(self, operation: Operation[T]):
        """
        Initialize builder with an operation.

        Args:
            operation: Initial operation
        """
        self._operation = operation
        self._transformations: list[Callable[[T], Any]] = []
        self._error_handlers: list[Callable[[Exception], None]] = []
        self._validators: list[Callable[[OperationContext], list[str]]] = []

    def then(self, next_operation: "Operation[U]") -> "OperationBuilder[U]":
        """
        Chain another operation after this one.

        Args:
            next_operation: Operation to execute next

        Returns:
            New builder for the chained operation
        """
        return ChainedOperationBuilder(self._operation, next_operation)

    def transform(self, func: Callable[[T], U]) -> "OperationBuilder[U]":
        """
        Transform the result of this operation.

        Args:
            func: Transformation function

        Returns:
            New builder with transformation
        """
        return TransformedOperationBuilder(self._operation, func)

    def on_error(self, handler: Callable[[Exception], None]) -> "OperationBuilder[T]":
        """
        Add error handler.

        Args:
            handler: Function to call on error

        Returns:
            Self for chaining
        """
        self._error_handlers.append(handler)
        return self

    def validate_with(
        self, validator: Callable[[OperationContext], list[str]]
    ) -> "OperationBuilder[T]":
        """
        Add validation function.

        Args:
            validator: Validation function

        Returns:
            Self for chaining
        """
        self._validators.append(validator)
        return self

    def build(self) -> Operation[T]:
        """
        Build the final operation.

        Returns:
            Composed operation
        """
        return self._operation

    def run(self, context: OperationContext) -> OperationResult[T]:
        """
        Execute the operation with context.

        Args:
            context: Execution context

        Returns:
            Operation result
        """
        # Run custom validators
        validation_errors = []
        for validator in self._validators:
            errors = validator(context)
            validation_errors.extend(errors)

        # Run operation's own validation
        validation_errors.extend(self._operation.validate(context))

        if validation_errors:
            error_msg = "; ".join(validation_errors)
            error = ValueError(f"Validation failed: {error_msg}")
            return OperationResult.failure(error, error_msg)

        # Execute operation
        try:
            result = self._operation.execute(context)
            return result
        except Exception as e:
            # Call error handlers
            for handler in self._error_handlers:
                try:
                    handler(e)
                except Exception as handler_error:
                    logger.error(f"Error handler failed: {handler_error}", exc_info=True)

            return OperationResult.failure(e, str(e))


class ChainedOperationBuilder(OperationBuilder[U], Generic[T, U]):
    """Builder for chained operations."""

    def __init__(self, first: Operation[T], second: Operation[U]):
        """Initialize with two operations to chain."""

        class ChainedOperation(Operation[U]):
            """Operation that chains two operations."""

            def describe(self) -> str:
                return f"{first.describe()} → {second.describe()}"

            def validate(self, context: OperationContext) -> list[str]:
                errors = first.validate(context)
                errors.extend(second.validate(context))
                return errors

            def execute(self, context: OperationContext) -> OperationResult[U]:
                # Execute first operation
                first_result = first.execute(context)
                if not first_result.is_success():
                    return OperationResult(
                        status=first_result.status,
                        error=first_result.error,
                        message=first_result.message,
                    )

                # Execute second operation
                return second.execute(context)

        super().__init__(ChainedOperation())


class TransformedOperationBuilder(OperationBuilder[U], Generic[T, U]):
    """Builder for operations with transformations."""

    def __init__(self, operation: Operation[T], transform: Callable[[T], U]):
        """Initialize with operation and transformation."""

        class TransformedOperation(Operation[U]):
            """Operation with result transformation."""

            def describe(self) -> str:
                return f"{operation.describe()} → transform"

            def validate(self, context: OperationContext) -> list[str]:
                return operation.validate(context)

            def execute(self, context: OperationContext) -> OperationResult[U]:
                result = operation.execute(context)
                if not result.is_success():
                    return OperationResult(
                        status=result.status,
                        error=result.error,
                        message=result.message,
                    )

                try:
                    transformed = transform(result.unwrap())
                    return OperationResult.success(transformed, result.message)
                except Exception as e:
                    return OperationResult.failure(e, f"Transformation failed: {e}")

        super().__init__(TransformedOperation())
