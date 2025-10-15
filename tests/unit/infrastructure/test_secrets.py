"""Tests for secrets management."""

from dom.infrastructure.secrets.manager import SecretsManager


def test_secrets_manager_create(mock_secrets_dir):
    """Test creating a secrets manager."""
    manager = SecretsManager(mock_secrets_dir)
    assert manager.secrets_dir == mock_secrets_dir
    assert manager.key_file.exists()


def test_secrets_set_and_get(mock_secrets_dir):
    """Test setting and getting secrets."""
    manager = SecretsManager(mock_secrets_dir)

    manager.set("test_key", "test_value")
    value = manager.get("test_key")

    assert value == "test_value"


def test_secrets_get_nonexistent(mock_secrets_dir):
    """Test getting a non-existent secret returns None."""
    manager = SecretsManager(mock_secrets_dir)
    value = manager.get("nonexistent_key")

    assert value is None


def test_secrets_get_with_default(mock_secrets_dir):
    """Test getting a non-existent secret with default value."""
    manager = SecretsManager(mock_secrets_dir)
    value = manager.get("nonexistent_key", "default_value")

    assert value == "default_value"


def test_secrets_set_if_not_exists(mock_secrets_dir):
    """Test set_if_not_exists only sets if key doesn't exist."""
    manager = SecretsManager(mock_secrets_dir)

    # First call should set the value
    result1 = manager.set_if_not_exists("test_key", "value1")
    assert result1 is True
    assert manager.get("test_key") == "value1"

    # Second call should not overwrite
    result2 = manager.set_if_not_exists("test_key", "value2")
    assert result2 is False
    assert manager.get("test_key") == "value1"


def test_secrets_generate_and_store(mock_secrets_dir):
    """Test generate_and_store creates a random secret."""
    manager = SecretsManager(mock_secrets_dir)

    secret = manager.generate_and_store("random_key", length=16)

    assert len(secret) == 16
    assert manager.get("random_key") == secret

    # Second call should return the same value
    secret2 = manager.generate_and_store("random_key", length=16)
    assert secret2 == secret


def test_secrets_delete(mock_secrets_dir):
    """Test deleting secrets."""
    manager = SecretsManager(mock_secrets_dir)

    manager.set("test_key", "test_value")
    assert manager.get("test_key") == "test_value"

    deleted = manager.delete("test_key")
    assert deleted is True
    assert manager.get("test_key") is None

    # Deleting again should return False
    deleted2 = manager.delete("test_key")
    assert deleted2 is False


def test_secrets_clear_all(mock_secrets_dir):
    """Test clearing all secrets."""
    manager = SecretsManager(mock_secrets_dir)

    manager.set("key1", "value1")
    manager.set("key2", "value2")

    manager.clear_all()

    assert manager.get("key1") is None
    assert manager.get("key2") is None


def test_secrets_persistence(mock_secrets_dir):
    """Test that secrets persist across manager instances."""
    manager1 = SecretsManager(mock_secrets_dir)
    manager1.set("persistent_key", "persistent_value")

    # Create a new manager instance
    manager2 = SecretsManager(mock_secrets_dir)
    value = manager2.get("persistent_key")

    assert value == "persistent_value"


def test_secrets_deterministic_password(mock_secrets_dir):
    """Test deterministic password generation."""
    manager = SecretsManager(mock_secrets_dir)

    # Set admin password first
    manager.set("admin_password", "admin123")

    # Generate deterministic password
    password1 = manager.generate_deterministic_password("team1", length=10)
    password2 = manager.generate_deterministic_password("team1", length=10)

    # Same seed should produce same password
    assert password1 == password2
    assert len(password1) == 10

    # Different seed should produce different password
    password3 = manager.generate_deterministic_password("team2", length=10)
    assert password3 != password1
