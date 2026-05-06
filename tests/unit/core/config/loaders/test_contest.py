"""Tests for the contest config loader.

These tests focus on `load_contest_from_config` orchestration and
`load_contests_from_config` post-processing (team sorting, username/password
assignment). Heavy problem-archive loading is mocked.
"""

from datetime import datetime
from unittest.mock import patch

from pydantic import SecretStr

from dom.core.config.loaders.contest import (
    load_contest_from_config,
    load_contests_from_config,
)
from dom.types.config.raw import RawContestConfig, RawTeam
from dom.types.secrets import SecretsProvider


class FakeSecretsProvider(SecretsProvider):
    def __init__(self):
        self._store: dict[str, str] = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def get_required(self, key):
        return self._store[key]

    def set(self, key, value):
        self._store[key] = value

    def set_if_not_exists(self, key, value):
        if key in self._store:
            return False
        self._store[key] = value
        return True

    def generate_and_store(self, key, length=32):
        value = f"gen-{key}"
        self._store[key] = value
        return value

    def delete(self, key):
        return self._store.pop(key, None) is not None

    def clear_all(self):
        self._store.clear()

    def generate_deterministic_password(self, seed, length=32):
        return SecretStr(f"pw-{seed}")

    def get_or_create_hash_seed(self):
        return "0" * 32


def _make_raw_contest(name: str = "Test Contest", teams=None) -> RawContestConfig:
    """Build a RawContestConfig that bypasses problem/team file loading."""
    return RawContestConfig(
        name=name,
        shortname=name.replace(" ", "_").upper(),
        formal_name=None,
        start_time=datetime(2026, 1, 1),
        duration="05:00:00.000",
        penalty_time=20,
        allow_submit=True,
        problems=[],
        teams=teams if teams is not None else [],
    )


# ---------------------------------------------------------------------------
# load_contest_from_config
# ---------------------------------------------------------------------------


def test_load_contest_passes_through_raw_fields(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    raw = _make_raw_contest(name="WF 2026")
    secrets = FakeSecretsProvider()

    with (
        patch(
            "dom.core.config.loaders.contest.load_problems_from_config", return_value=[]
        ) as load_problems,
        patch(
            "dom.core.config.loaders.contest.load_teams_from_config", return_value=[]
        ) as load_teams,
    ):
        contest = load_contest_from_config(raw, config_path, secrets)

    load_problems.assert_called_once_with(raw.problems, config_path=config_path)
    load_teams.assert_called_once_with(raw.teams, config_path=config_path, secrets=secrets)

    assert contest.name == "WF 2026"
    assert contest.shortname == "WF_2026"
    assert contest.duration == "05:00:00.000"
    assert contest.penalty_time == 20
    assert contest.allow_submit is True
    assert contest.problems == []
    assert contest.teams == []


def test_load_contest_invokes_problem_letter_assignment(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    raw = _make_raw_contest()
    secrets = FakeSecretsProvider()

    with (
        patch("dom.core.config.loaders.contest.load_problems_from_config", return_value=[]),
        patch("dom.core.config.loaders.contest.load_teams_from_config", return_value=[]),
        patch("dom.core.config.loaders.contest.assign_problem_letters", return_value=[]) as assign,
    ):
        load_contest_from_config(raw, config_path, secrets)

    assign.assert_called_once_with([])


# ---------------------------------------------------------------------------
# load_contests_from_config: post-processing
# ---------------------------------------------------------------------------


def _raw_teams() -> list[RawTeam]:
    return [
        RawTeam(name="Charlie", affiliation="Org C", country="USA"),
        RawTeam(name="Alpha", affiliation="Org A", country="USA"),
        RawTeam(name="Bravo", affiliation="Org B", country="USA"),
    ]


def test_load_contests_sorts_teams_by_name(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    raw = _make_raw_contest(teams=_raw_teams())
    secrets = FakeSecretsProvider()

    with (
        patch("dom.core.config.loaders.contest.load_problems_from_config", return_value=[]),
        # Pass through the inline list of RawTeams as actual Team objects.
        # Use loader's normal path by NOT patching teams loader.
    ):
        contests = load_contests_from_config([raw], config_path, secrets)

    assert len(contests) == 1
    assert [t.name for t in contests[0].teams] == ["Alpha", "Bravo", "Charlie"]


def test_load_contests_assigns_usernames_and_passwords(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    raw = _make_raw_contest(teams=_raw_teams())
    secrets = FakeSecretsProvider()

    with patch("dom.core.config.loaders.contest.load_problems_from_config", return_value=[]):
        contests = load_contests_from_config([raw], config_path, secrets)

    teams = contests[0].teams
    # Every team must get a username and a non-empty password.
    assert all(t.username for t in teams)
    assert all(t.password.get_secret_value() for t in teams)
    # Usernames are unique across teams.
    assert len({t.username for t in teams}) == len(teams)


def test_load_contests_processes_each_contest(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    raws = [_make_raw_contest(name="One"), _make_raw_contest(name="Two")]
    secrets = FakeSecretsProvider()

    with (
        patch("dom.core.config.loaders.contest.load_problems_from_config", return_value=[]),
        patch("dom.core.config.loaders.contest.load_teams_from_config", return_value=[]),
    ):
        contests = load_contests_from_config(raws, config_path, secrets)

    assert [c.name for c in contests] == ["One", "Two"]
