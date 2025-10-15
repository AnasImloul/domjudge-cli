"""Input validators for CLI commands.

This module provides Typer-compatible validators using the centralized validation rules.
All validation logic is defined in dom.validation.rules and adapted here for CLI use.
"""

from pathlib import Path

from dom.validation import ValidationRules, for_typer

# ------------------------------------------------------------
# Pre-built validators for common CLI inputs
# All use centralized ValidationRules - SINGLE SOURCE OF TRUTH
# ------------------------------------------------------------


def validate_contest_name(value: str | None) -> str | None:
    """
    Validate contest name format.

    Uses: ValidationRules.contest_name()
    Rules: See dom.validation.rules.ValidationRules.contest_name()
    """
    return for_typer(ValidationRules.contest_name())(value)  # type: ignore[no-any-return]


def validate_file_path(value: str | None) -> Path | None:
    """
    Validate YAML configuration file path and convert to Path object.

    Uses: ValidationRules.config_file_path()
    Rules: See dom.validation.rules.ValidationRules.config_file_path()
    """
    if value is None:
        return None
    validated = for_typer(ValidationRules.config_file_path())(value)
    return Path(validated) if validated else None


def validate_port(value: int | None) -> int | None:
    """
    Validate port number.

    Uses: ValidationRules.port()
    Rules: See dom.validation.rules.ValidationRules.port()
    """
    if value is None:
        return None
    return for_typer(ValidationRules.port())(value)  # type: ignore[no-any-return]


def validate_judges_count(value: int | None) -> int | None:
    """
    Validate number of judgehosts.

    Uses: ValidationRules.judges_count()
    Rules: See dom.validation.rules.ValidationRules.judges_count()
    """
    if value is None:
        return None
    return for_typer(ValidationRules.judges_count())(value)  # type: ignore[no-any-return]


# ------------------------------------------------------------
# Additional validators for extended functionality
# ------------------------------------------------------------


def validate_shortname(value: str | None) -> str | None:
    """
    Validate contest shortname.

    Uses: ValidationRules.contest_shortname()
    Rules: See dom.validation.rules.ValidationRules.contest_shortname()
    """
    return for_typer(ValidationRules.contest_shortname())(value)  # type: ignore[no-any-return]


def validate_email(value: str | None) -> str | None:
    """
    Validate email address format.

    Uses: ValidationRules.email()
    Rules: See dom.validation.rules.ValidationRules.email()
    """
    return for_typer(ValidationRules.email())(value)  # type: ignore[no-any-return]


def validate_url(value: str | None) -> str | None:
    """
    Validate URL format.

    Uses: ValidationRules.url()
    Rules: See dom.validation.rules.ValidationRules.url()
    """
    return for_typer(ValidationRules.url())(value)  # type: ignore[no-any-return]
