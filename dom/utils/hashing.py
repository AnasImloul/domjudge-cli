"""Deterministic hashing utilities for team ID generation.

This module provides deterministic hashing functions for generating team IDs.
The hash seed is managed by the SecretsManager to ensure proper integration
with the application's secrets management system.
"""

import hashlib

from dom.types.secrets import SecretsProvider


def deterministic_hash(secrets: SecretsProvider, value: str, modulo: int = 10000) -> int:
    """
    Generate deterministic hash for a given value.

    Uses MD5 with a stored seed to ensure the same value always produces
    the same hash, even across different Python processes.

    Args:
        secrets: Secrets manager instance
        value: Value to hash
        modulo: Modulo to apply to hash result (default: 10000 for 4-digit IDs)

    Returns:
        Deterministic hash value as integer

    Example:
        >>> deterministic_hash(secrets, "Team Alpha|INSEA|USA")  # Always returns same value
        2375
    """
    # Get hash seed from secrets manager
    seed = secrets.get_or_create_hash_seed()

    # Combine seed with value for deterministic hashing
    combined = f"{seed}:{value}"

    # Use MD5 for deterministic hash (not for security, just for consistency)
    hash_bytes = hashlib.md5(combined.encode(), usedforsecurity=False).digest()

    # Convert to integer and apply modulo
    hash_value = int.from_bytes(hash_bytes[:4], "big") % modulo

    return hash_value


def generate_team_username(secrets: SecretsProvider, composite_key: str) -> str:
    """
    Generate deterministic team username from composite key.

    Args:
        secrets: Secrets manager instance
        composite_key: Team composite key (format: "name|affiliation|country")

    Returns:
        Team username (format: "team####")

    Example:
        >>> generate_team_username(secrets, "Team Alpha|INSEA|USA")
        "team2375"
    """
    hash_value = deterministic_hash(secrets, composite_key, modulo=10000)
    return f"team{hash_value:04d}"
