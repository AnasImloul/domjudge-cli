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
    """Base exception for API-related errors."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code (if applicable)
            response_body: Response body (if applicable)
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class RetryableAPIError(APIError):
    """Raised when an API error is transient and can be retried.

    Examples: 5xx server errors, network timeouts, connection errors.
    """

    pass


class PermanentAPIError(APIError):
    """Raised when an API error is permanent and should not be retried.

    Examples: 4xx client errors (except 429), authentication failures.
    """

    pass


class APIRateLimitError(RetryableAPIError):
    """Raised when API rate limit is exceeded (HTTP 429).

    This is retryable but should respect Retry-After header.
    """

    pass


class APIAuthenticationError(PermanentAPIError):
    """Raised when API authentication fails (HTTP 401/403).

    This is permanent - retrying with same credentials will fail.
    """

    pass


class APINotFoundError(PermanentAPIError):
    """Raised when a requested resource is not found via API (HTTP 404).

    This is permanent - resource does not exist.
    """

    pass


class APIServerError(RetryableAPIError):
    """Raised when server returns 5xx error.

    These are typically transient and worth retrying.
    """

    pass


class APINetworkError(RetryableAPIError):
    """Raised when network communication fails.

    Examples: Connection refused, timeout, DNS failure.
    """

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
