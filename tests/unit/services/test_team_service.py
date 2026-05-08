"""Tests for TeamService."""

from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from dom.core.services.base import ServiceContext
from dom.core.services.team.apply import TeamService
from dom.exceptions import APIError, TeamError
from dom.types.secrets import SecretsProvider
from dom.types.team import Team


def _team(
    name: str = "Alpha",
    affiliation: str | None = "MIT",
    country: str | None = "USA",
    username: str = "team1",
) -> Team:
    return Team(
        name=name,
        affiliation=affiliation,
        country=country,
        username=username,
        password=SecretStr("hunter2"),
    )


@pytest.fixture
def client():
    """Mock matching the DomJudgeAPIProtocol surface used by TeamService."""
    c = MagicMock()
    c.organizations.add_to_contest.return_value = MagicMock(id="org-1")
    c.teams.add_to_contest.return_value = MagicMock(id="team-1", created=True)
    return c


@pytest.fixture
def secrets():
    s = MagicMock(spec=SecretsProvider)
    s.get_required.return_value = "deterministic-seed"
    return s


@pytest.fixture
def service(client, secrets):
    return TeamService(client, secrets)


@pytest.fixture
def context(client):
    return ServiceContext(client=client, contest_id="c1", team_group_id="g1")


# ---------------------------------------------------------------- create


def test_create_returns_failure_when_contest_id_missing(service, client):
    ctx = ServiceContext(client=client)
    result = service.create(_team(), ctx)

    assert result.success is False
    assert isinstance(result.error, ValueError)
    client.teams.add_to_contest.assert_not_called()


def test_create_creates_organization_when_team_has_affiliation(service, client, context):
    service.create(_team(affiliation="MIT", country="USA"), context)

    client.organizations.add_to_contest.assert_called_once()
    org_arg = client.organizations.add_to_contest.call_args.kwargs["organization"]
    assert org_arg.name == "MIT"
    assert org_arg.country == "USA"


def test_create_skips_organization_when_team_has_no_affiliation(service, client, context):
    service.create(_team(affiliation=None), context)

    client.organizations.add_to_contest.assert_not_called()
    client.teams.add_to_contest.assert_called_once()


def test_create_uses_contest_team_group_when_provided(service, client, context):
    service.create(_team(), context)

    team_arg = client.teams.add_to_contest.call_args.kwargs["team_data"]
    assert team_arg.group_ids == ["g1"]


def test_create_falls_back_to_default_group_when_unset(service, client):
    ctx = ServiceContext(client=client, contest_id="c1")  # no team_group_id
    service.create(_team(), ctx)

    team_arg = client.teams.add_to_contest.call_args.kwargs["team_data"]
    assert team_arg.group_ids != ["g1"]
    assert len(team_arg.group_ids) == 1  # default group set


def test_create_marks_created_true_when_api_says_created(service, client, context):
    client.teams.add_to_contest.return_value = MagicMock(id="team-7", created=True)
    result = service.create(_team(name="Alpha"), context)

    assert result.success is True
    assert result.created is True
    client.users.add.assert_called_once()  # user created on first creation


def test_create_skips_user_creation_when_team_already_exists(service, client, context):
    """Idempotency: pre-existing team → no user creation, but still success."""
    client.teams.add_to_contest.return_value = MagicMock(id="team-7", created=False)

    result = service.create(_team(), context)

    assert result.success is True
    assert result.created is False
    client.users.add.assert_not_called()


def test_create_wraps_api_error_as_team_error(service, client, context):
    client.teams.add_to_contest.side_effect = APIError("boom", status_code=500)

    result = service.create(_team(name="Beta"), context)

    assert result.success is False
    assert isinstance(result.error, TeamError)
    assert "Beta" in str(result.error)


def test_create_uses_display_name_distinct_from_join_name(service, client, context):
    """``display_name`` is human-readable; ``name`` is the composite join key."""
    service.create(_team(name="Alpha", username="team1"), context)

    team_arg = client.teams.add_to_contest.call_args.kwargs["team_data"]
    assert team_arg.display_name == "Alpha"
    # composite name embeds the username and composite_key
    assert team_arg.name.startswith("team1|Alpha|")


# ---------------------------------------------------------------- create_many


def test_create_many_returns_one_result_per_input(service, client, context):
    client.teams.add_to_contest.return_value = MagicMock(id="t", created=True)

    results = service.create_many(
        [_team(name=n, username=f"u{i}") for i, n in enumerate(["A", "B", "C"])],
        context,
    )

    assert len(results) == 3
    assert all(r.success for r in results)


def test_create_many_collects_partial_failures(service, client, context):
    def fake_add(*, contest_id, team_data):
        if "broken" in team_data.display_name:
            raise APIError("nope", status_code=400)
        return MagicMock(id="t", created=True)

    client.teams.add_to_contest.side_effect = fake_add

    results = service.create_many(
        [
            _team(name="ok1", username="u1"),
            _team(name="broken", username="u2"),
            _team(name="ok2", username="u3"),
        ],
        context,
    )

    assert len(results) == 3
    assert sum(1 for r in results if r.success) == 2
    assert sum(1 for r in results if not r.success) == 1


def test_create_many_summary_counts_match(service, client, context):
    client.teams.add_to_contest.side_effect = [
        MagicMock(id="t1", created=True),
        APIError("x", status_code=500),
        MagicMock(id="t3", created=False),  # already exists
    ]

    results = service.create_many(
        [_team(name=f"T{i}", username=f"u{i}") for i in range(3)], context
    )
    summary = service.get_summary(results)

    assert summary["total"] == 3
    assert summary["successful"] == 2
    assert summary["failed"] == 1
    assert summary["created"] == 1  # only one was newly created
