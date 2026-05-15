"""Deterministic hashing utilities for team ID generation.

This module provides deterministic hashing functions for generating team IDs.
The hash seed is managed by the SecretsManager to ensure proper integration
with the application's secrets management system.
"""

import hashlib

from dom.types.secrets import SecretsProvider


def deterministic_hash(secrets: SecretsProvider, value: str, modulo: int = 10000) -> int:
    """
    Generate a deterministic hash for ``value``.

    The salt is derived from the admin password (via
    ``SecretsProvider.get_username_hash_seed``), so the same config
    produces the same hash on any machine — matching the cross-machine
    determinism already guaranteed for team passwords.

    Args:
        secrets: Secrets manager instance
        value: Value to hash
        modulo: Modulo to apply to hash result (default: 10000 for 4-digit IDs)

    Returns:
        Deterministic hash value as integer
    """
    seed = secrets.get_username_hash_seed()
    combined = f"{seed}:{value}"
    hash_bytes = hashlib.md5(combined.encode(), usedforsecurity=False).digest()
    return int.from_bytes(hash_bytes[:4], "big") % modulo


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
