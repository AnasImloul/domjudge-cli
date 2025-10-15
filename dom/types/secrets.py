"""Secrets management interface types."""

from abc import ABC, abstractmethod

from pydantic import SecretStr


class SecretsProvider(ABC):
    """
    Abstract interface for secrets management.

    This interface defines the contract for secrets storage and retrieval,
    allowing the operations layer to depend on an abstraction rather than
    concrete infrastructure implementation.

    The interface matches the existing SecretsManager API to avoid
    forcing implementation changes.
    """

    @abstractmethod
    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a secret by key.

        Args:
            key: Secret identifier
            default: Default value if secret doesn't exist

        Returns:
            Secret value or default
        """
        ...

    @abstractmethod
    def get_required(self, key: str) -> str:
        """
        Retrieve a required secret by key.

        Args:
            key: Secret identifier

        Returns:
            Secret value

        Raises:
            SecretsError: If secret doesn't exist
        """
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """
        Store a secret.

        Args:
            key: Secret identifier
            value: Secret value to store
        """
        ...

    @abstractmethod
    def set_if_not_exists(self, key: str, value: str) -> bool:
        """
        Store a secret only if it doesn't already exist.

        Args:
            key: Secret identifier
            value: Secret value to store

        Returns:
            True if secret was set, False if it already existed
        """
        ...

    @abstractmethod
    def generate_and_store(self, key: str, length: int = 32) -> str:
        """
        Generate a random secret and store it if it doesn't exist.

        Args:
            key: Secret identifier
            length: Length of random secret to generate

        Returns:
            The secret value (existing or newly generated)
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret identifier

        Returns:
            True if secret was deleted, False if it didn't exist
        """
        ...

    @abstractmethod
    def clear_all(self) -> None:
        """Delete all secrets."""
        ...

    @abstractmethod
    def generate_deterministic_password(self, seed: str, length: int = 32) -> SecretStr:
        """
        Generate a deterministic password based on a seed and the admin password.

        This is useful for team passwords that need to be reproducible but still
        tied to the admin secret.

        Args:
            seed: Seed string (e.g., team name)
            length: Password length

        Returns:
            Deterministic password

        Raises:
            SecretsError: If admin_password is not set
        """
        ...
