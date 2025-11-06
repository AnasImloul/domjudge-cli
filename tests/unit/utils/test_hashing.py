"""Tests for deterministic hashing utilities."""

from dom.infrastructure.secrets.manager import SecretsManager
from dom.utils.hashing import deterministic_hash, generate_team_username


class TestDeterministicHashing:
    """Tests for deterministic hashing functions."""

    def test_deterministic_hash_returns_same_value_for_same_input(self, tmp_path):
        """Test that the same input always produces the same hash."""
        secrets = SecretsManager(tmp_path)
        secrets.get_or_create_hash_seed()

        value = "Team Alpha|INSEA|USA"

        hash1 = deterministic_hash(secrets, value)
        hash2 = deterministic_hash(secrets, value)
        hash3 = deterministic_hash(secrets, value)

        assert hash1 == hash2 == hash3

    def test_deterministic_hash_returns_different_values_for_different_inputs(self, tmp_path):
        """Test that different inputs produce different hashes."""
        secrets = SecretsManager(tmp_path)
        secrets.get_or_create_hash_seed()

        hash1 = deterministic_hash(secrets, "Team Alpha|INSEA|USA")
        hash2 = deterministic_hash(secrets, "Team Beta|INPT|USA")
        hash3 = deterministic_hash(secrets, "Team Gamma|ENSIAS|USA")

        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3

    def test_deterministic_hash_stays_same_across_sessions(self, tmp_path):
        """Test that hash values persist across sessions (same seed)."""
        # First session
        secrets1 = SecretsManager(tmp_path)
        value = "Team Alpha|INSEA|USA"
        hash1 = deterministic_hash(secrets1, value)

        # Second session (new instance, same storage)
        secrets2 = SecretsManager(tmp_path)
        hash2 = deterministic_hash(secrets2, value)

        # Should be identical because same seed is loaded
        assert hash1 == hash2

    def test_deterministic_hash_respects_modulo(self, tmp_path):
        """Test that modulo parameter limits the hash value."""
        secrets = SecretsManager(tmp_path)

        # Test with modulo 100 (2-digit hashes)
        hash_value = deterministic_hash(secrets, "test", modulo=100)
        assert 0 <= hash_value < 100

        # Test with modulo 10000 (4-digit hashes, default)
        hash_value = deterministic_hash(secrets, "test", modulo=10000)
        assert 0 <= hash_value < 10000

    def test_generate_team_username_format(self, tmp_path):
        """Test that team usernames have the correct format."""
        secrets = SecretsManager(tmp_path)

        username = generate_team_username(secrets, "Team Alpha|INSEA|USA")

        assert username.startswith("team")
        assert len(username) == 8  # "team" + 4 digits
        assert username[4:].isdigit()

    def test_generate_team_username_is_deterministic(self, tmp_path):
        """Test that the same team key always generates the same username."""
        secrets = SecretsManager(tmp_path)
        composite_key = "Team Alpha|INSEA|USA"

        username1 = generate_team_username(secrets, composite_key)
        username2 = generate_team_username(secrets, composite_key)
        username3 = generate_team_username(secrets, composite_key)

        assert username1 == username2 == username3

    def test_generate_team_username_unique_for_different_teams(self, tmp_path):
        """Test that different teams get different usernames."""
        secrets = SecretsManager(tmp_path)

        username1 = generate_team_username(secrets, "Team Alpha|INSEA|USA")
        username2 = generate_team_username(secrets, "Team Beta|INPT|USA")
        username3 = generate_team_username(secrets, "Team Gamma|ENSIAS|USA")

        # All should be different
        assert username1 != username2
        assert username2 != username3
        assert username1 != username3

    def test_generate_team_username_same_name_different_org(self, tmp_path):
        """Test that same team name with different org gets different username."""
        secrets = SecretsManager(tmp_path)

        # Same name, different organizations
        username1 = generate_team_username(secrets, "Team Alpha|INSEA|USA")
        username2 = generate_team_username(secrets, "Team Alpha|INPT|USA")

        # Should be different because composite key is different
        assert username1 != username2

    def test_generate_team_username_same_name_different_country(self, tmp_path):
        """Test that same team name with different country gets different username."""
        secrets = SecretsManager(tmp_path)

        # Same name and org, different countries
        username1 = generate_team_username(secrets, "Team Alpha|INSEA|USA")
        username2 = generate_team_username(secrets, "Team Alpha|INSEA|MAR")

        # Should be different because composite key is different
        assert username1 != username2

    def test_deterministic_hash_uses_stored_seed(self, tmp_path):
        """Test that hash function uses the seed from SecretsManager."""
        secrets = SecretsManager(tmp_path)

        # Generate a seed
        seed = secrets.get_or_create_hash_seed()
        assert seed is not None
        assert len(seed) == 32  # 16 bytes = 32 hex chars

        # Use it for hashing
        hash_value = deterministic_hash(secrets, "test")

        # Should be a valid integer
        assert isinstance(hash_value, int)
        assert hash_value >= 0

    def test_hash_collision_rate_is_reasonable(self, tmp_path):
        """Test that hash collisions are rare with realistic data."""
        secrets = SecretsManager(tmp_path)

        # Generate 100 different team composite keys
        hashes = set()
        for i in range(100):
            composite_key = f"Team {i}|University {i}|Country {i}"
            hash_value = deterministic_hash(secrets, composite_key, modulo=10000)
            hashes.add(hash_value)

        # With 100 teams and 10000 possible values, we should have very few collisions
        # Expect at least 95% unique (allowing for birthday paradox)
        assert len(hashes) >= 95


class TestHashSeedManagement:
    """Tests for hash seed management in SecretsManager."""

    def test_hash_seed_is_generated_on_first_call(self, tmp_path):
        """Test that a hash seed is generated on first access."""
        secrets = SecretsManager(tmp_path)

        seed = secrets.get_or_create_hash_seed()

        assert seed is not None
        assert isinstance(seed, str)
        assert len(seed) == 32  # 16 bytes in hex

    def test_hash_seed_is_reused_on_subsequent_calls(self, tmp_path):
        """Test that the same seed is returned on subsequent calls."""
        secrets = SecretsManager(tmp_path)

        seed1 = secrets.get_or_create_hash_seed()
        seed2 = secrets.get_or_create_hash_seed()
        seed3 = secrets.get_or_create_hash_seed()

        assert seed1 == seed2 == seed3

    def test_hash_seed_persists_across_instances(self, tmp_path):
        """Test that seed is stored and can be loaded by new instance."""
        # Create and store seed
        secrets1 = SecretsManager(tmp_path)
        seed1 = secrets1.get_or_create_hash_seed()

        # Load in new instance
        secrets2 = SecretsManager(tmp_path)
        seed2 = secrets2.get_or_create_hash_seed()

        assert seed1 == seed2

    def test_hash_seed_is_random_and_unpredictable(self, tmp_path):
        """Test that different directories get different seeds."""
        secrets1 = SecretsManager(tmp_path / "dir1")
        secrets2 = SecretsManager(tmp_path / "dir2")

        seed1 = secrets1.get_or_create_hash_seed()
        seed2 = secrets2.get_or_create_hash_seed()

        # Different secrets managers should have different seeds
        assert seed1 != seed2
