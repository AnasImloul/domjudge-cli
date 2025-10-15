"""Declarative validation framework with composable validators.

This module provides a declarative way to define and compose validation rules
that can be easily tested and reused across the codebase.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class ValidationError:
    """Represents a validation error with context."""

    field: str
    message: str
    code: str | None = None
    value: Any | None = None

    def __str__(self) -> str:
        """Format error message."""
        return f"{self.field}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation with list of errors."""

    errors: list[ValidationError]

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0

    def add_error(self, error: ValidationError) -> None:
        """Add a validation error."""
        self.errors.append(error)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge with another validation result."""
        return ValidationResult(errors=self.errors + other.errors)

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(errors=[])

    @classmethod
    def failure(cls, field: str, message: str, code: str | None = None) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(errors=[ValidationError(field=field, message=message, code=code)])


class Validator(ABC, Generic[T]):
    """
    Base class for declarative validators.

    Validators encapsulate validation logic in a composable way.
    They can be combined using logical operators and chained together.

    Example:
        >>> validator = (
        ...     Required("username")
        ...     & MinLength("username", 3)
        ...     & MaxLength("username", 20)
        ... )
        >>> result = validator.validate({"username": "ab"})
        >>> assert not result.is_valid()
    """

    @abstractmethod
    def validate(self, value: T) -> ValidationResult:
        """
        Validate the value.

        Args:
            value: Value to validate

        Returns:
            Validation result with any errors
        """

    def __and__(self, other: "Validator[T]") -> "Validator[T]":
        """Combine validators with AND logic."""
        return AndValidator(self, other)

    def __or__(self, other: "Validator[T]") -> "Validator[T]":
        """Combine validators with OR logic."""
        return OrValidator(self, other)

    def __invert__(self) -> "Validator[T]":
        """Negate validator."""
        return NotValidator(self)


class AndValidator(Validator[T]):
    """Combines two validators with AND logic."""

    def __init__(self, left: Validator[T], right: Validator[T]):
        """Initialize with two validators."""
        self.left = left
        self.right = right

    def validate(self, value: T) -> ValidationResult:
        """Validate with both validators."""
        left_result = self.left.validate(value)
        right_result = self.right.validate(value)
        return left_result.merge(right_result)


class OrValidator(Validator[T]):
    """Combines two validators with OR logic."""

    def __init__(self, left: Validator[T], right: Validator[T]):
        """Initialize with two validators."""
        self.left = left
        self.right = right

    def validate(self, value: T) -> ValidationResult:
        """Validate with either validator."""
        left_result = self.left.validate(value)
        if left_result.is_valid():
            return left_result
        right_result = self.right.validate(value)
        if right_result.is_valid():
            return right_result
        # Both failed, return combined errors
        return left_result.merge(right_result)


class NotValidator(Validator[T]):
    """Negates a validator."""

    def __init__(self, validator: Validator[T]):
        """Initialize with validator to negate."""
        self.validator = validator

    def validate(self, value: T) -> ValidationResult:
        """Validate by negating inner validator."""
        result = self.validator.validate(value)
        if result.is_valid():
            return ValidationResult.failure("value", "Validation should have failed")
        return ValidationResult.success()


class FunctionValidator(Validator[T]):
    """Validator that wraps a function."""

    def __init__(
        self,
        func: Callable[[T], bool],
        field: str,
        message: str,
        code: str | None = None,
    ):
        """
        Initialize with validation function.

        Args:
            func: Function that returns True if valid
            field: Field name for error messages
            message: Error message if validation fails
            code: Optional error code
        """
        self.func = func
        self.field = field
        self.message = message
        self.code = code

    def validate(self, value: T) -> ValidationResult:
        """Validate using the function."""
        try:
            if self.func(value):
                return ValidationResult.success()
            return ValidationResult.failure(self.field, self.message, self.code)
        except Exception as e:
            return ValidationResult.failure(
                self.field, f"Validation error: {e}", "validation_exception"
            )


# Common validators


class Required(Validator[dict[str, Any]]):
    """Validates that a field is present and not None."""

    def __init__(self, field: str):
        """Initialize with field name."""
        self.field = field

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate field is present."""
        if self.field not in value or value[self.field] is None:
            return ValidationResult.failure(self.field, "Field is required", "required")
        return ValidationResult.success()


class MinLength(Validator[dict[str, Any]]):
    """Validates minimum length of a string field."""

    def __init__(self, field: str, min_length: int):
        """Initialize with field name and minimum length."""
        self.field = field
        self.min_length = min_length

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate minimum length."""
        field_value = value.get(self.field)
        if field_value is None:
            return ValidationResult.success()  # Skip if not present
        if len(str(field_value)) < self.min_length:
            return ValidationResult.failure(
                self.field,
                f"Must be at least {self.min_length} characters",
                "min_length",
            )
        return ValidationResult.success()


class MaxLength(Validator[dict[str, Any]]):
    """Validates maximum length of a string field."""

    def __init__(self, field: str, max_length: int):
        """Initialize with field name and maximum length."""
        self.field = field
        self.max_length = max_length

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate maximum length."""
        field_value = value.get(self.field)
        if field_value is None:
            return ValidationResult.success()  # Skip if not present
        if len(str(field_value)) > self.max_length:
            return ValidationResult.failure(
                self.field,
                f"Must be at most {self.max_length} characters",
                "max_length",
            )
        return ValidationResult.success()


class Pattern(Validator[dict[str, Any]]):
    """Validates that a field matches a regex pattern."""

    def __init__(self, field: str, pattern: str, message: str | None = None):
        """Initialize with field name and pattern."""
        self.field = field
        self.pattern = re.compile(pattern)
        self.message = message or f"Must match pattern {pattern}"

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate pattern match."""
        field_value = value.get(self.field)
        if field_value is None:
            return ValidationResult.success()  # Skip if not present
        if not self.pattern.match(str(field_value)):
            return ValidationResult.failure(self.field, self.message, "pattern")
        return ValidationResult.success()


class Range(Validator[dict[str, Any]]):
    """Validates that a numeric field is within a range."""

    def __init__(self, field: str, min_val: float | None = None, max_val: float | None = None):
        """Initialize with field name and range."""
        self.field = field
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate range."""
        field_value = value.get(self.field)
        if field_value is None:
            return ValidationResult.success()  # Skip if not present

        try:
            num_value = float(field_value)
        except (ValueError, TypeError):
            return ValidationResult.failure(self.field, "Must be a number", "type_error")

        if self.min_val is not None and num_value < self.min_val:
            return ValidationResult.failure(
                self.field, f"Must be at least {self.min_val}", "min_value"
            )
        if self.max_val is not None and num_value > self.max_val:
            return ValidationResult.failure(
                self.field, f"Must be at most {self.max_val}", "max_value"
            )
        return ValidationResult.success()


class OneOf(Validator[dict[str, Any]]):
    """Validates that a field value is one of allowed values."""

    def __init__(self, field: str, allowed_values: list[Any]):
        """Initialize with field name and allowed values."""
        self.field = field
        self.allowed_values = allowed_values

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate value is in allowed list."""
        field_value = value.get(self.field)
        if field_value is None:
            return ValidationResult.success()  # Skip if not present
        if field_value not in self.allowed_values:
            allowed_str = ", ".join(str(v) for v in self.allowed_values)
            return ValidationResult.failure(
                self.field, f"Must be one of: {allowed_str}", "invalid_choice"
            )
        return ValidationResult.success()


class Schema(Validator[dict[str, Any]]):
    """Validates an object against a schema of field validators."""

    def __init__(self, **field_validators: Validator[dict[str, Any]]):
        """
        Initialize with field validators.

        Args:
            **field_validators: Mapping of field names to validators
        """
        self.field_validators = field_validators

    def validate(self, value: dict[str, Any]) -> ValidationResult:
        """Validate all fields."""
        result = ValidationResult.success()
        for _field, validator in self.field_validators.items():
            field_result = validator.validate(value)
            result = result.merge(field_result)
        return result
