"""Password hashing utilities using bcrypt.

This module provides secure password hashing functionality for DOMjudge.
Uses bcrypt with appropriate rounds to match htpasswd behavior.
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Uses 5 rounds to match htpasswd -B behavior, providing a balance
    between security and performance for contest environments.

    Args:
        password: Plain text password to hash

    Returns:
        BCrypt hashed password string

    Example:
        >>> hashed = hash_password("admin123")
        >>> hashed.startswith('$2b$')
        True
    """
    salt = bcrypt.gensalt(rounds=5)  # rounds=5 to match htpasswd -B behavior
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


# Alias for backward compatibility and clarity
generate_bcrypt_password = hash_password
