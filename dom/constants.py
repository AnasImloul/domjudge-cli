"""Application-wide constants for DOMjudge CLI.

This module contains configuration constants used throughout the application.
These values can be overridden through configuration files or environment variables.
"""

from enum import Enum

# ============================================================
# Secret Keys
# ============================================================


class SecretKeys(str, Enum):
    """
    Enumeration of all secret keys used in the application.

    Using an enum instead of magic strings provides:
    - Compile-time checking (import errors instead of runtime KeyErrors)
    - IDE autocompletion
    - Easy refactoring (find all usages)
    - Self-documentation

    Usage:
        >>> secrets.get(SecretKeys.ADMIN_PASSWORD.value)
        >>> secrets.set(SecretKeys.DB_PASSWORD.value, "secret")
    """

    # Infrastructure secrets
    ADMIN_PASSWORD = "admin_password"  # nosec B105
    DB_PASSWORD = "db_password"  # nosec B105
    JUDGEDAEMON_PASSWORD = "judgedaemon_password"  # nosec B105

    # API credentials
    API_USERNAME = "api_username"
    API_PASSWORD = "api_password"  # nosec B105

    # Deterministic hashing
    HASH_SEED = "hash_seed"  # nosec B105  # Seed for deterministic team ID generation

    # Contest-specific secrets
    TEAM_PASSWORD_PREFIX = "team_password_"  # nosec B105  # Followed by team ID

    @classmethod
    def team_password_key(cls, team_id: str) -> str:
        """
        Generate a team-specific password key.

        Args:
            team_id: Team identifier

        Returns:
            Secret key for the team's password

        Example:
            >>> SecretKeys.team_password_key("team-123")
            'team_password_team-123'
        """
        return f"{cls.TEAM_PASSWORD_PREFIX.value}{team_id}"


# ============================================================
# ID Generation
# ============================================================

# Large prime modulus for generating deterministic IDs from hashes
# Using 10^9 + 7 (common in competitive programming for its mathematical properties)
HASH_MODULUS = int(1e9 + 7)


# ============================================================
# DOMjudge Default Values
# ============================================================

# Default team group ID (Participants group in DOMjudge)
# Group IDs in DOMjudge:
#   1 = Observers
#   2 = Staff
#   3 = Participants (default for contest teams)
#   4 = Jury
DEFAULT_TEAM_GROUP_ID = "3"

# Default country code for organizations when not specified
# ISO 3166-1 alpha-3 country code
DEFAULT_COUNTRY_CODE = "MAR"


# ============================================================
# Concurrency & Performance
# ============================================================

# Maximum concurrent team additions to avoid overwhelming the API
# This works in conjunction with the rate limiter
MAX_CONCURRENT_TEAM_OPERATIONS = 5

# Maximum concurrent problem additions
MAX_CONCURRENT_PROBLEM_OPERATIONS = 3


# ============================================================
# API & Caching
# ============================================================

# Default cache TTL in seconds for API responses
DEFAULT_CACHE_TTL = 300  # 5 minutes

# Cache TTL for frequently changing data (contests list)
SHORT_CACHE_TTL = 60  # 1 minute

# Cache TTL for rarely changing data (all problems)
LONG_CACHE_TTL = 600  # 10 minutes

# Default rate limit (requests per second)
DEFAULT_RATE_LIMIT = 10.0

# Default rate limit burst capacity
DEFAULT_RATE_BURST = 20


# ============================================================
# Security & Secrets
# ============================================================

# Default password length for generated passwords
DEFAULT_PASSWORD_LENGTH = 16

# Minimum password length for validation
MIN_PASSWORD_LENGTH = 8

# Maximum password length
MAX_PASSWORD_LENGTH = 128


# ============================================================
# Docker & Infrastructure
# ============================================================

# Container name prefix for DOMjudge services
CONTAINER_PREFIX = "dom-cli"

# Default health check timeout in seconds
HEALTH_CHECK_TIMEOUT = 60

# Health check polling interval in seconds
HEALTH_CHECK_INTERVAL = 2


class ContainerNames(str, Enum):
    """Container name constants for DOMjudge infrastructure.

    Usage:
        container_name = ContainerNames.DOMSERVER.with_prefix(prefix)
        # Returns: "prefix-domserver"
    """

    DOMSERVER = "domserver"
    MARIADB = "mariadb"
    MYSQL_CLIENT = "mysql-client"
    JUDGEHOST = "judgehost"

    def with_prefix(self, prefix: str) -> str:
        """Get full container name with prefix.

        Args:
            prefix: Container prefix (e.g., 'domjudge-abc123')

        Returns:
            Full container name (e.g., 'domjudge-abc123-domserver')
        """
        return f"{prefix}-{self.value}"


# ============================================================
# Validation Limits
# ============================================================

# Maximum contest name length
MAX_CONTEST_NAME_LENGTH = 100

# Maximum contest shortname length
MAX_CONTEST_SHORTNAME_LENGTH = 50

# Maximum team name length
MAX_TEAM_NAME_LENGTH = 100

# Maximum problem name length
MAX_PROBLEM_NAME_LENGTH = 100

# Port range validation
MIN_PORT = 1
MAX_PORT = 65535
MIN_UNPRIVILEGED_PORT = 1024


# ============================================================
# File System
# ============================================================

# Default DOMjudge CLI directory name
DOM_DIRECTORY_NAME = ".dom"

# Supported config file names (in order of precedence)
CONFIG_FILE_NAMES = ["dom-judge.yaml", "dom-judge.yml"]

# Supported config file extensions
CONFIG_FILE_EXTENSIONS = [".yaml", ".yml"]


# ============================================================
# Logging
# ============================================================

# Default log file name
LOG_FILE_NAME = "domjudge-cli.log"

# Default log level
DEFAULT_LOG_LEVEL = "INFO"
