"""Application-wide constants for DOMjudge CLI.

This module contains configuration constants used throughout the application.
These values can be overridden through configuration files or environment variables.
"""

from enum import Enum

# ============================================================
# Secret Keys
# ============================================================


class SecretKeys(str, Enum):
    """Enumeration of secret keys used in the application.

    Note: Most of the codebase passes secret-key string literals directly
    rather than going through this enum — only HASH_SEED is read via this
    indirection (see dom/infrastructure/secrets/manager.py).
    """

    HASH_SEED = "hash_seed"  # nosec B105  # Seed for deterministic team ID generation


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
