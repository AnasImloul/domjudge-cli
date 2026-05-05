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
