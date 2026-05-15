"""Tests for deterministic hashing utilities."""

import pytest

from dom.exceptions import SecretsError
from dom.infrastructure.secrets.manager import SecretsManager
from dom.utils.hashing import deterministic_hash, generate_team_username


def _make_secrets(tmp_path, admin_password: str = "shared-admin-pw") -> SecretsManager:
    """Create a SecretsManager with the admin password set."""
    secrets = SecretsManager(tmp_path)
    secrets.set("admin_password", admin_password)
    return secrets


class TestDeterministicHashing:
    """Tests for deterministic hashing functions."""

    def test_deterministic_hash_returns_same_value_for_same_input(self, tmp_path):
        secrets = _make_secrets(tmp_path)
        value = "Team Alpha|INSEA|USA"

        hash1 = deterministic_hash(secrets, value)
        hash2 = deterministic_hash(secrets, value)
        hash3 = deterministic_hash(secrets, value)

        assert hash1 == hash2 == hash3

    def test_deterministic_hash_returns_different_values_for_different_inputs(self, tmp_path):
        secrets = _make_secrets(tmp_path)

        hash1 = deterministic_hash(secrets, "Team Alpha|INSEA|USA")
        hash2 = deterministic_hash(secrets, "Team Beta|INPT|USA")
        hash3 = deterministic_hash(secrets, "Team Gamma|ENSIAS|USA")

        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3

    def test_deterministic_hash_is_same_across_machines_with_same_admin_password(self, tmp_path):
        """The same admin password on two distinct storage dirs must yield identical hashes."""
        machine_a = _make_secrets(tmp_path / "a", admin_password="shared-pw")
        machine_b = _make_secrets(tmp_path / "b", admin_password="shared-pw")

        value = "Team Alpha|INSEA|USA"
        assert deterministic_hash(machine_a, value) == deterministic_hash(machine_b, value)

    def test_deterministic_hash_differs_when_admin_password_differs(self, tmp_path):
        """Different admin passwords must yield different hashes (acts as a tenant boundary)."""
        secrets_a = _make_secrets(tmp_path / "a", admin_password="pw-one")
        secrets_b = _make_secrets(tmp_path / "b", admin_password="pw-two")

        value = "Team Alpha|INSEA|USA"
        assert deterministic_hash(secrets_a, value) != deterministic_hash(secrets_b, value)

    def test_deterministic_hash_respects_modulo(self, tmp_path):
        secrets = _make_secrets(tmp_path)

        assert 0 <= deterministic_hash(secrets, "test", modulo=100) < 100
        assert 0 <= deterministic_hash(secrets, "test", modulo=10000) < 10000

    def test_deterministic_hash_requires_admin_password(self, tmp_path):
        secrets = SecretsManager(tmp_path)  # no admin_password set

        with pytest.raises(SecretsError):
            deterministic_hash(secrets, "Team Alpha|INSEA|USA")


class TestGenerateTeamUsername:
    """Tests for ``generate_team_username``."""

    def test_format(self, tmp_path):
        secrets = _make_secrets(tmp_path)
        username = generate_team_username(secrets, "Team Alpha|INSEA|USA")

        assert username.startswith("team")
        assert len(username) == 8  # "team" + 4 digits
        assert username[4:].isdigit()

    def test_is_deterministic(self, tmp_path):
        secrets = _make_secrets(tmp_path)
        composite_key = "Team Alpha|INSEA|USA"

        username1 = generate_team_username(secrets, composite_key)
        username2 = generate_team_username(secrets, composite_key)
        username3 = generate_team_username(secrets, composite_key)

        assert username1 == username2 == username3

    def test_unique_for_different_teams(self, tmp_path):
        secrets = _make_secrets(tmp_path)

        username1 = generate_team_username(secrets, "Team Alpha|INSEA|USA")
        username2 = generate_team_username(secrets, "Team Beta|INPT|USA")
        username3 = generate_team_username(secrets, "Team Gamma|ENSIAS|USA")

        assert username1 != username2
        assert username2 != username3
        assert username1 != username3

    def test_same_name_different_org(self, tmp_path):
        secrets = _make_secrets(tmp_path)

        username1 = generate_team_username(secrets, "Team Alpha|INSEA|USA")
        username2 = generate_team_username(secrets, "Team Alpha|INPT|USA")

        assert username1 != username2

    def test_same_name_different_country(self, tmp_path):
        secrets = _make_secrets(tmp_path)

        username1 = generate_team_username(secrets, "Team Alpha|INSEA|USA")
        username2 = generate_team_username(secrets, "Team Alpha|INSEA|MAR")

        assert username1 != username2

    def test_is_same_across_machines_with_same_admin_password(self, tmp_path):
        """Regression: two machines sharing the same config produce identical usernames."""
        machine_a = _make_secrets(tmp_path / "a", admin_password="shared-pw")
        machine_b = _make_secrets(tmp_path / "b", admin_password="shared-pw")

        composite_key = "Team Alpha|INSEA|USA"
        assert generate_team_username(machine_a, composite_key) == generate_team_username(
            machine_b, composite_key
        )

    def test_collision_rate_is_reasonable(self, tmp_path):
        """With 100 distinct teams in 10000 buckets, collisions should be rare."""
        secrets = _make_secrets(tmp_path)

        hashes = {
            deterministic_hash(secrets, f"Team {i}|University {i}|Country {i}", modulo=10000)
            for i in range(100)
        }
        assert len(hashes) >= 95
