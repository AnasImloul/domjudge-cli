"""Adapters to convert ValidationRules to different formats.

This module provides functions to adapt ValidatorBuilder instances to:
- Pydantic field validators (for config files)
- Typer callbacks (for CLI arguments)
- Prompt parsers (for interactive input)
"""

from collections.abc import Callable
from typing import Any

import typer

from dom.utils.validators import Invalid, ValidatorBuilder


def for_pydantic(validator: ValidatorBuilder) -> Callable:
    """
    Adapt a ValidatorBuilder for use as a Pydantic field_validator.

    Args:
        validator: ValidatorBuilder instance with validation rules

    Returns:
        Function suitable for use with @field_validator decorator

    Example:
        from dom.validation import ValidationRules, for_pydantic

        class MyModel(BaseModel):
            port: int

            validate_port = field_validator('port')(for_pydantic(ValidationRules.port()))
    """
    validator_fn = validator.build()

    def pydantic_validator(_cls, v: Any) -> Any:
        """Pydantic validator that uses our validation rules."""
        if v is None:
            return v
        try:
            return validator_fn(str(v))
        except Invalid as e:
            # Pydantic expects ValueError
            raise ValueError(str(e)) from e

    return classmethod(pydantic_validator)  # type: ignore[return-value]


def for_typer(validator: ValidatorBuilder) -> Callable:
    """
    Adapt a ValidatorBuilder for use as a Typer callback.

    Args:
        validator: ValidatorBuilder instance with validation rules

    Returns:
        Function suitable for use as a Typer callback

    Example:
        from dom.validation import ValidationRules, for_typer

        @app.command()
        def command(
            port: int = typer.Option(..., callback=for_typer(ValidationRules.port()))
        ):
            ...
    """
    validator_fn = validator.build()

    def typer_callback(value: Any | None) -> Any | None:
        """Typer callback that uses our validation rules."""
        if value is None:
            return None
        try:
            return validator_fn(str(value))
        except Invalid as e:
            raise typer.BadParameter(str(e)) from e

    return typer_callback


def for_prompt(validator: ValidatorBuilder) -> Callable[[str], Any]:
    """
    Adapt a ValidatorBuilder for use as a prompt parser.

    Args:
        validator: ValidatorBuilder instance with validation rules

    Returns:
        Function suitable for use with ask() prompt parser

    Example:
        from dom.validation import ValidationRules, for_prompt
        from dom.utils.prompt import ask

        port = ask(
            "Port number",
            default="8080",
            parser=for_prompt(ValidationRules.port())
        )
    """
    return validator.build()


# Convenience functions for common patterns


def optional_for_pydantic(validator: ValidatorBuilder) -> Callable:
    """
    Adapt a ValidatorBuilder for optional Pydantic fields.

    Returns None if value is None, otherwise validates.
    """
    validator_fn = validator.build()

    def pydantic_validator(_cls, v: Any | None) -> Any | None:
        if v is None:
            return None
        try:
            return validator_fn(str(v))
        except Invalid as e:
            raise ValueError(str(e)) from e

    return classmethod(pydantic_validator)  # type: ignore[return-value]


def with_default_for_typer(validator: ValidatorBuilder, default: Any) -> Callable:
    """
    Adapt a ValidatorBuilder for Typer with a default value.

    If no value provided, returns default. Otherwise validates.
    """
    validator_fn = validator.build()

    def typer_callback(value: Any | None) -> Any:
        if value is None:
            return default
        try:
            return validator_fn(str(value))
        except Invalid as e:
            raise typer.BadParameter(str(e)) from e

    return typer_callback
