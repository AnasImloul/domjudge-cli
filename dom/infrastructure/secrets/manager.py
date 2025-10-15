"""Secrets management with encryption.

This module provides secure storage and retrieval of secrets using Fernet encryption
from the cryptography library. Secrets are encrypted at rest and only decrypted when needed.
"""

import json
import random
import secrets
import stat
import string
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import SecretStr

from dom.constants import DEFAULT_PASSWORD_LENGTH
from dom.exceptions import SecretsError
from dom.logging_config import get_logger
from dom.types.secrets import SecretsProvider

logger = get_logger(__name__)

# Thread-safe lock for random state manipulation
_random_lock = threading.Lock()


@contextmanager
def deterministic_random(seed: str) -> Iterator[None]:
    """
    Context manager for deterministic random generation.

    This context manager temporarily sets the random seed for reproducible
    random generation within its scope, then restores the previous random state.
    It is thread-safe and does not affect random generation outside the context.

    Args:
        seed: Seed string for deterministic generation

    Yields:
        None

    Example:
        >>> with deterministic_random("my-seed"):
        ...     val1 = random.randint(1, 100)
        ...     val2 = random.choice(['a', 'b', 'c'])
        >>> # Random state is restored here
        >>> # Multiple calls with same seed produce same results:
        >>> with deterministic_random("my-seed"):
        ...     assert random.randint(1, 100) == val1

    Thread Safety:
        Uses a lock to ensure thread-safe access to the global random state.
    """
    with _random_lock:
        # Save current random state
        state = random.getstate()
        try:
            # Set deterministic seed
            random.seed(seed)
            yield
        finally:
            # Restore previous state
            random.setstate(state)


class SecretsManager(SecretsProvider):
    """
    Secure secrets manager with encryption at rest.

    Secrets are stored in an encrypted JSON file using Fernet symmetric encryption.
    The encryption key is derived from a key file stored separately.

    Example:
        >>> from pathlib import Path
        >>> manager = SecretsManager(Path(".dom"))
        >>> manager.set_secret("api_key", "secret123")
        >>> value = manager.get_secret("api_key")
    """

    def __init__(self, secrets_dir: Path):
        """
        Initialize the secrets manager.

        Args:
            secrets_dir: Directory to store secrets and encryption key
        """
        self.secrets_dir = Path(secrets_dir)
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

        # Set secure permissions on directory (owner read/write/execute only)
        self.secrets_dir.chmod(stat.S_IRWXU)

        self.key_file = self.secrets_dir / ".key"
        self.secrets_file = self.secrets_dir / "secrets.enc"

        self._ensure_key_exists()
        self._fernet = Fernet(self._load_key())

    def _ensure_key_exists(self) -> None:
        """Ensure encryption key exists, create if not."""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            # Set secure permissions (owner read/write only)
            self.key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            logger.debug(f"Generated new encryption key at {self.key_file}")

    def _load_key(self) -> bytes:
        """Load the encryption key from disk."""
        try:
            return self.key_file.read_bytes()
        except Exception as e:
            raise SecretsError(f"Failed to load encryption key: {e}") from e

    def _load_secrets(self) -> dict[str, str]:
        """Load and decrypt all secrets from disk."""
        if not self.secrets_file.exists():
            return {}

        try:
            encrypted_data = self.secrets_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode("utf-8"))
            return dict(data) if isinstance(data, dict) else {}
        except Exception as e:
            raise SecretsError(f"Failed to load secrets: {e}") from e

    def _save_secrets(self, secrets: dict) -> None:
        """Encrypt and save all secrets to disk."""
        try:
            json_data = json.dumps(secrets, indent=2)
            encrypted_data = self._fernet.encrypt(json_data.encode("utf-8"))
            self.secrets_file.write_bytes(encrypted_data)
            # Set secure permissions (owner read/write only)
            self.secrets_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            logger.debug(f"Saved encrypted secrets to {self.secrets_file}")
        except Exception as e:
            raise SecretsError(f"Failed to save secrets: {e}") from e

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a secret by key.

        Args:
            key: Secret identifier
            default: Default value if secret doesn't exist

        Returns:
            Secret value or default
        """
        secrets = self._load_secrets()
        value = secrets.get(key, default)
        if value is not None:
            logger.debug(f"Retrieved secret '{key}'")
        return value

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
        value = self.get(key)
        if value is None:
            raise SecretsError(f"Required secret '{key}' not found")
        return value

    def set(self, key: str, value: str) -> None:
        """
        Store a secret.

        Args:
            key: Secret identifier
            value: Secret value to store
        """
        secrets = self._load_secrets()
        secrets[key] = value
        self._save_secrets(secrets)
        logger.info(f"Stored secret '{key}'")

    def set_if_not_exists(self, key: str, value: str) -> bool:
        """
        Store a secret only if it doesn't already exist.

        Args:
            key: Secret identifier
            value: Secret value to store

        Returns:
            True if secret was set, False if it already existed
        """
        secrets = self._load_secrets()
        if key in secrets:
            logger.debug(f"Secret '{key}' already exists, not overwriting")
            return False

        secrets[key] = value
        self._save_secrets(secrets)
        logger.info(f"Stored new secret '{key}'")
        return True

    def generate_and_store(self, key: str, length: int = DEFAULT_PASSWORD_LENGTH) -> str:
        """
        Generate a random secret and store it if it doesn't exist.

        Args:
            key: Secret identifier
            length: Length of random secret to generate

        Returns:
            The secret value (existing or newly generated)
        """
        existing = self.get(key)
        if existing:
            logger.debug(f"Using existing secret '{key}'")
            return existing

        alphabet = string.ascii_letters + string.digits
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        self.set(key, value)
        logger.info(f"Generated and stored new secret '{key}'")
        return value

    def delete(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret identifier

        Returns:
            True if secret was deleted, False if it didn't exist
        """
        secrets_data = self._load_secrets()
        if key not in secrets_data:
            return False

        del secrets_data[key]
        self._save_secrets(secrets_data)
        logger.info(f"Deleted secret '{key}'")
        return True

    def clear_all(self) -> None:
        """Delete all secrets."""
        if self.secrets_file.exists():
            self.secrets_file.unlink()
            logger.warning("Cleared all secrets")

    def generate_deterministic_password(
        self, seed: str, length: int = DEFAULT_PASSWORD_LENGTH
    ) -> SecretStr:
        """
        Generate a deterministic password based on a seed and the admin password.

        This is useful for team passwords that need to be reproducible but still
        tied to the admin secret. Uses the deterministic_random context manager
        to ensure thread-safety and no side effects on global random state.

        Args:
            seed: Seed string (e.g., team name)
            length: Password length

        Returns:
            Deterministic password

        Raises:
            SecretsError: If admin_password is not set
        """
        admin_password = self.get("admin_password")
        if not admin_password:
            raise SecretsError("Admin password not set, cannot generate deterministic password")

        combined_seed = admin_password + seed

        # Use context manager for thread-safe deterministic generation
        # that doesn't affect global random state
        with deterministic_random(combined_seed):
            alphabet = string.ascii_letters + string.digits
            password = "".join(random.choice(alphabet) for _ in range(length))  # nosec B311

        logger.debug(f"Generated deterministic password for seed '{seed}'")
        return SecretStr(password)


def generate_random_string(length: int = DEFAULT_PASSWORD_LENGTH) -> str:
    """
    Generate a random string of specified length.

    Args:
        length: Length of the string to generate

    Returns:
        Random string containing ASCII letters and digits
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
