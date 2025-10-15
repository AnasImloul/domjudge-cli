"""Central validation rules for all DOMjudge configuration values.

This module defines validation logic once and provides it in multiple formats.
This is the SINGLE SOURCE OF TRUTH for validation rules.
"""

import warnings

from dom.constants import (
    MAX_CONTEST_NAME_LENGTH,
    MAX_CONTEST_SHORTNAME_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from dom.utils.validators import ValidatorBuilder


class ValidationRules:
    """
    Central repository of all validation rules.

    Each method returns a ValidatorBuilder that can be adapted for:
    - Pydantic (config files)
    - Typer (CLI arguments)
    - Prompts (interactive init)

    Usage:
        # For prompt
        port_validator = ValidationRules.port().build()

        # For Pydantic
        from dom.validation import for_pydantic
        validate_port = for_pydantic(ValidationRules.port())

        # For Typer
        from dom.validation import for_typer
        validate_port = for_typer(ValidationRules.port())
    """

    # ============================================================
    # Infrastructure Validation
    # ============================================================

    @staticmethod
    def port(warn_privileged: bool = True) -> ValidatorBuilder:
        """
        Validate port number.

        Rules:
        - Must be 1-65535
        - Warn if < 1024 (requires privileges)

        Args:
            warn_privileged: Whether to warn about privileged ports
        """
        builder = ValidatorBuilder.port()

        if warn_privileged:
            builder = builder.unprivileged()

        return builder

    @staticmethod
    def judges_count() -> ValidatorBuilder:
        """
        Validate number of judgehosts.

        Rules:
        - Must be >= 1 (at least one judge required)
        - Warn if > 16 (unusually high for typical setups)
        """
        builder = ValidatorBuilder.integer().min(1)

        # Warn if unusually high
        def check_reasonable(count: int) -> None:
            if count > 16:
                warnings.warn(
                    f"Number of judges ({count}) is unusually high - this may impact performance",
                    UserWarning,
                    stacklevel=2,
                )

        return builder.satisfy(check_reasonable)

    @staticmethod
    def password() -> ValidatorBuilder:
        """
        Validate password.

        Rules:
        - Must be 8-128 characters
        """
        return (
            ValidatorBuilder.string()
            .min_length(MIN_PASSWORD_LENGTH)
            .max_length(MAX_PASSWORD_LENGTH)
        )

    # ============================================================
    # Contest Validation
    # ============================================================

    @staticmethod
    def contest_name() -> ValidatorBuilder:
        """
        Validate contest name.

        Rules:
        - Cannot be empty
        - Max 100 characters
        - Trimmed of whitespace
        """
        return (
            ValidatorBuilder.string()
            .strip()
            .non_empty("Contest name cannot be empty")
            .max_length(MAX_CONTEST_NAME_LENGTH)
        )

    @staticmethod
    def contest_shortname() -> ValidatorBuilder:
        """
        Validate contest shortname.

        Rules:
        - Cannot be empty
        - Max 50 characters
        - Only alphanumeric, dashes, underscores (no spaces)
        - Trimmed and uppercased
        """
        return (
            ValidatorBuilder.string()
            .strip()
            .upper()
            .non_empty("Contest shortname cannot be empty")
            .max_length(MAX_CONTEST_SHORTNAME_LENGTH)
            .matches(
                r"^[A-Z0-9_\-]+$",
                message="Contest shortname can only contain uppercase letters, numbers, dashes, and underscores",
            )
        )

    @staticmethod
    def penalty_time() -> ValidatorBuilder:
        """
        Validate penalty time in minutes.

        Rules:
        - Must be non-negative
        - Warn if > 1000 (unusually high)
        """
        builder = ValidatorBuilder.integer().non_negative()

        def check_reasonable(time: int) -> None:
            if time > 1000:
                warnings.warn(f"Penalty time ({time}) is unusually high", UserWarning, stacklevel=2)

        return builder.satisfy(check_reasonable)

    @staticmethod
    def duration() -> ValidatorBuilder:
        """
        Validate contest duration format.

        Rules:
        - Format: "HH:MM:SS" or "HH:MM:SS.mmm"
        """
        return ValidatorBuilder.string().matches(
            r"^\d+:\d{2}:\d{2}(\.\d{3})?$",
            message="Duration must be in format 'HH:MM:SS' or 'HH:MM:SS.mmm'",
        )

    # ============================================================
    # File Path Validation
    # ============================================================

    @staticmethod
    def config_file_path() -> ValidatorBuilder:
        """
        Validate YAML configuration file path.

        Rules:
        - Must exist
        - Must be a file (not directory)
        - Must have .yaml or .yml extension
        - Path normalized (~ expanded)
        """
        return (
            ValidatorBuilder.path()
            .normalize()
            .must_exist()
            .must_be_file()
            .allowed_extensions([".yaml", ".yml"])
        )

    @staticmethod
    def problem_archive_path() -> ValidatorBuilder:
        """
        Validate problem archive file path.

        Rules:
        - Must exist
        - Must be a file
        - Must have .zip extension
        """
        return (
            ValidatorBuilder.path()
            .normalize()
            .must_exist()
            .must_be_file()
            .allowed_extensions([".zip"])
        )

    @staticmethod
    def teams_file_path() -> ValidatorBuilder:
        """
        Validate teams CSV/TSV file path.

        Rules:
        - Must exist
        - Must be a file
        - Must have .csv, .tsv, or .txt extension
        """
        return (
            ValidatorBuilder.path()
            .normalize()
            .must_exist()
            .must_be_file()
            .allowed_extensions([".csv", ".tsv", ".txt"])
        )

    # ============================================================
    # Team Validation
    # ============================================================

    @staticmethod
    def team_name() -> ValidatorBuilder:
        """
        Validate team name.

        Rules:
        - Cannot be empty
        - Max 100 characters
        """
        return (
            ValidatorBuilder.string().strip().non_empty("Team name cannot be empty").max_length(100)
        )

    @staticmethod
    def organization_name() -> ValidatorBuilder:
        """
        Validate organization/affiliation name.

        Rules:
        - Max 200 characters if provided
        """
        return ValidatorBuilder.string().strip().max_length(200)

    # ============================================================
    # Email Validation
    # ============================================================

    @staticmethod
    def email() -> ValidatorBuilder:
        """
        Validate email address.

        Rules:
        - Basic email format
        - Normalized to lowercase
        """
        return (
            ValidatorBuilder.string()
            .strip()
            .lower()
            .non_empty("Email cannot be empty")
            .matches(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                message="Invalid email address format",
            )
        )

    # ============================================================
    # URL Validation
    # ============================================================

    @staticmethod
    def url() -> ValidatorBuilder:
        """
        Validate URL.

        Rules:
        - Must start with http:// or https://
        - Basic URL structure validation
        """
        return (
            ValidatorBuilder.string()
            .strip()
            .non_empty("URL cannot be empty")
            .matches(
                r"^https?://[^\s/$.?#].[^\s]*$",
                message="Invalid URL format. Must start with http:// or https://",
            )
        )
