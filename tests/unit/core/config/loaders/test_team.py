"""Tests for team config loader."""

from pydantic import SecretStr

from dom.constants import DEFAULT_COUNTRY_CODE
from dom.core.config.loaders.team import load_teams_from_config
from dom.types.config.raw import RawTeamsConfig
from dom.types.secrets import SecretsProvider


class FakeSecretsProvider(SecretsProvider):
    def get(self, key, default=None):
        return default

    def get_required(self, key):
        return ""

    def set(self, key, value):
        pass

    def set_if_not_exists(self, key, value):
        return True

    def generate_and_store(self, key, length=32):
        return ""

    def delete(self, key):
        return False

    def clear_all(self):
        pass

    def generate_deterministic_password(self, seed, length=32):
        return SecretStr(f"pw-{seed}")

    def get_username_hash_seed(self):
        return "0" * 32


def test_blank_country_cell_falls_back_to_default(tmp_path):
    """Empty country column value should produce DEFAULT_COUNTRY_CODE, not ''."""
    csv_file = tmp_path / "teams.csv"
    csv_file.write_text("id,name,affiliation,country\n1,Team A,Org A,\n")
    config_path = tmp_path / "contest.yml"

    team_config = RawTeamsConfig(
        **{
            "from": "teams.csv",
            "delimiter": ",",
            "rows": "2-2",
            "name": "$2",
            "affiliation": "$3",
            "country": "$4",
        }
    )

    teams = load_teams_from_config(team_config, config_path, FakeSecretsProvider())

    assert len(teams) == 1
    assert teams[0].country == DEFAULT_COUNTRY_CODE


def test_present_country_is_preserved(tmp_path):
    csv_file = tmp_path / "teams.csv"
    csv_file.write_text("id,name,affiliation,country\n1,Team A,Org A,FRA\n")
    config_path = tmp_path / "contest.yml"

    team_config = RawTeamsConfig(
        **{
            "from": "teams.csv",
            "delimiter": ",",
            "rows": "2-2",
            "name": "$2",
            "affiliation": "$3",
            "country": "$4",
        }
    )

    teams = load_teams_from_config(team_config, config_path, FakeSecretsProvider())

    assert teams[0].country == "FRA"
