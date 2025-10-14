"""Custom exceptions for DOMjudge CLI.

This module defines a comprehensive exception hierarchy for better error handling
and debugging throughout the application.
"""


class DomJudgeCliError(Exception):
    """Base exception for all DOMjudge CLI errors."""

    pass


class ConfigError(DomJudgeCliError):
    """Raised when there's an error in configuration loading or parsing."""

    pass


class InfrastructureError(DomJudgeCliError):
    """Raised when infrastructure operations fail."""

    pass


class DockerError(InfrastructureError):
    """Raised when Docker operations fail."""

    pass


class APIError(DomJudgeCliError):
    """Raised when API requests to DOMjudge fail."""

    pass


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    pass


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""

    pass


class APINotFoundError(APIError):
    """Raised when a requested resource is not found via API."""

    pass


class SecretsError(DomJudgeCliError):
    """Raised when secrets management operations fail."""

    pass


class ProblemError(DomJudgeCliError):
    """Raised when problem-related operations fail."""

    pass


class ProblemLoadError(ProblemError):
    """Raised when loading or converting a problem fails."""

    pass


class ProblemValidationError(ProblemError):
    """Raised when problem validation fails."""

    pass


class TeamError(DomJudgeCliError):
    """Raised when team-related operations fail."""

    pass


class ContestError(DomJudgeCliError):
    """Raised when contest-related operations fail."""

    pass


class ValidationError(DomJudgeCliError):
    """Raised when validation of input data fails."""

    pass
