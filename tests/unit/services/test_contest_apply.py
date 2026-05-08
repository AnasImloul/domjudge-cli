"""Tests for ContestApplicationService.

The service is a flat toolkit — orchestration lives in
``dom.core.operations.contest.apply``. These tests exercise each
toolkit method in isolation.
"""

from unittest.mock import MagicMock

import pytest

from dom.core.services.base import ServiceContext
from dom.core.services.contest.apply import ContestApplicationService
from dom.core.services.contest.changes import (
    ChangeType,
    ContestChangeSet,
    FieldChange,
)
from dom.exceptions import ContestError
from dom.types.secrets import SecretsProvider


@pytest.fixture
def secrets():
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def client():
    c = MagicMock()
    c.contests.create.return_value = MagicMock(id="contest-1", created=True)
    c.groups.create_for_contest.return_value = MagicMock(id="group-1")
    return c


@pytest.fixture
def collaborators():
    problem = MagicMock()
    problem.create_many.return_value = []
    problem.get_summary.return_value = {"failed": 0, "successful": 0}
    team = MagicMock()
    team.create_many.return_value = []
    team.get_summary.return_value = {"failed": 0, "successful": 0}
    comparator = MagicMock()
    return problem, team, comparator


@pytest.fixture
def service(client, secrets, collaborators):
    problem, team, comparator = collaborators
    svc = ContestApplicationService(
        client,
        secrets,
        problem_service=problem,
        team_service=team,
        state_comparator=comparator,
    )
    return svc


def _contest(shortname="C0", name="Contest 0", problems=None, teams=None):
    c = MagicMock()
    c.shortname = shortname
    c.name = name
    c.formal_name = name
    c.start_time = "2026-01-01T10:00:00+00:00"
    c.duration = "5:00:00.000"
    c.allow_submit = True
    c.problems = problems or []
    c.teams = teams or []
    return c


def _change_set(change_type=ChangeType.CREATE, field_changes=None, existing_id=None):
    return ContestChangeSet(
        contest_shortname="C0",
        change_type=change_type,
        field_changes=field_changes or [],
        resource_changes=[],
        existing_contest_id=existing_id,
    )


# ---------------------------------------------------------------- compare


def test_compare_delegates_to_state_comparator(service, collaborators):
    _, _, comparator = collaborators
    expected = _change_set()
    comparator.compare_contest.return_value = expected

    result = service.compare(_contest())

    assert result is expected
    comparator.compare_contest.assert_called_once()


def test_compare_requires_shortname(service):
    contest = _contest(shortname=None)
    with pytest.raises(ContestError, match="shortname"):
        service.compare(contest)


# ---------------------------------------------------------------- resolve_or_create


def test_resolve_or_create_creates_new_contest(service, client):
    cs = _change_set(ChangeType.CREATE)
    contest_id, skipped = service.resolve_or_create(_contest(), cs)

    assert contest_id == "contest-1"
    assert skipped == []
    client.contests.create.assert_called_once()
    create_arg = client.contests.create.call_args.kwargs["contest_data"]
    assert create_arg.shortname == "C0"


def test_resolve_or_create_uses_existing_id_with_no_changes(service, client):
    cs = _change_set(ChangeType.NO_CHANGE, existing_id="existing-1")
    contest_id, skipped = service.resolve_or_create(_contest(), cs)

    assert contest_id == "existing-1"
    assert skipped == []
    client.contests.create.assert_not_called()


def test_resolve_or_create_returns_skipped_field_changes(service):
    fc = FieldChange(field="duration", old_value="5:00", new_value="6:00")
    cs = _change_set(ChangeType.UPDATE, field_changes=[fc], existing_id="existing-1")

    contest_id, skipped = service.resolve_or_create(_contest(), cs)

    assert contest_id == "existing-1"
    assert skipped == [fc]


def test_resolve_or_create_raises_when_existing_id_missing(service):
    cs = _change_set(ChangeType.UPDATE, existing_id=None)
    with pytest.raises(ContestError, match="no id was resolved"):
        service.resolve_or_create(_contest(), cs)


def test_resolve_or_create_wraps_create_error_as_contest_error(service, client):
    client.contests.create.side_effect = RuntimeError("upstream 500")
    cs = _change_set(ChangeType.CREATE)

    with pytest.raises(ContestError) as exc_info:
        service.resolve_or_create(_contest(), cs)
    assert "upstream 500" in str(exc_info.value)


# ---------------------------------------------------------------- provision_team_group


def test_provision_team_group_uses_contest_naming(service, client):
    group_id = service.provision_team_group("contest-1", "finals")

    assert group_id == "group-1"
    kwargs = client.groups.create_for_contest.call_args.kwargs
    assert kwargs["contest_id"] == "contest-1"
    assert kwargs["group_id"] == "finals-teams"
    assert "FINALS" in kwargs["name"]


# ---------------------------------------------------------------- apply_problems / apply_teams


def _ctx(client):
    return ServiceContext(client=client, contest_id="contest-1", contest_shortname="C0")


def test_apply_problems_invokes_service(service, collaborators, client):
    problem, _, _ = collaborators
    contest = _contest(problems=["p1", "p2"])

    service.apply_problems(contest, _ctx(client))

    problem.create_many.assert_called_once()
    assert problem.create_many.call_args.args[0] == ["p1", "p2"]


def test_apply_problems_raises_on_failure(service, collaborators, client):
    problem, _, _ = collaborators
    problem.get_summary.return_value = {"failed": 2, "successful": 1}

    with pytest.raises(ContestError):
        service.apply_problems(_contest(), _ctx(client))


def test_apply_teams_invokes_service(service, collaborators, client):
    _, team, _ = collaborators
    contest = _contest(teams=["t1", "t2", "t3"])

    service.apply_teams(contest, _ctx(client))

    team.create_many.assert_called_once()
    assert team.create_many.call_args.args[0] == ["t1", "t2", "t3"]


def test_apply_teams_raises_on_failure(service, collaborators, client):
    _, team, _ = collaborators
    team.get_summary.return_value = {"failed": 1, "successful": 0}

    with pytest.raises(ContestError):
        service.apply_teams(_contest(), _ctx(client))


# ---------------------------------------------------------------- constructor injection


def test_constructor_injection_wires_collaborators(client, secrets, collaborators):
    problem, team, comparator = collaborators

    svc = ContestApplicationService(
        client,
        secrets,
        problem_service=problem,
        team_service=team,
        state_comparator=comparator,
    )

    assert svc.problem_service is problem
    assert svc.team_service is team
    assert svc.state_comparator is comparator
