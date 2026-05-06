"""Tests for ContestApplicationService."""

from unittest.mock import MagicMock, patch

import pytest

from dom.core.services.contest.apply import ContestApplicationService, apply_contests
from dom.core.services.contest.state import ChangeType
from dom.exceptions import ContestError
from dom.types.secrets import SecretsProvider


@pytest.fixture
def secrets():
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def client():
    """API client with the call paths used by ContestApplicationService."""
    c = MagicMock()
    c.contests.create.return_value = MagicMock(id="contest-1", created=True)
    c.groups.create_for_contest.return_value = MagicMock(id="group-1")
    return c


@pytest.fixture
def service(client, secrets):
    """ContestApplicationService with all collaborators stubbed."""
    with (
        patch("dom.core.services.contest.apply.ProblemService") as ps_cls,
        patch("dom.core.services.contest.apply.TeamService") as ts_cls,
        patch("dom.core.services.contest.apply.ContestStateComparator") as cmp_cls,
    ):
        problem_service = MagicMock()
        problem_service.create_many.return_value = []
        problem_service.get_summary.return_value = {"failed": 0, "succeeded": 0}
        ps_cls.return_value = problem_service

        team_service = MagicMock()
        team_service.create_many.return_value = []
        team_service.get_summary.return_value = {"failed": 0, "succeeded": 0}
        ts_cls.return_value = team_service

        comparator = MagicMock()
        cmp_cls.return_value = comparator

        svc = ContestApplicationService(client, secrets)
        svc._problem_mock = problem_service  # type: ignore[attr-defined]
        svc._team_mock = team_service  # type: ignore[attr-defined]
        svc._comparator_mock = comparator  # type: ignore[attr-defined]
        yield svc


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


def _change_set(change_type=ChangeType.CREATE, field_changes=None):
    cs = MagicMock()
    cs.change_type = change_type
    cs.field_changes = field_changes or []
    return cs


# ---------------------------------------------------------------- apply_contest


def test_apply_contest_creates_when_change_type_is_create(service, client):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.CREATE)
    contest = _contest()

    contest_id = service.apply_contest(contest)

    assert contest_id == "contest-1"
    client.contests.create.assert_called_once()
    create_arg = client.contests.create.call_args.kwargs["contest_data"]
    assert create_arg.shortname == "C0"


def test_apply_contest_skips_creation_when_no_change(service, client):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.NO_CHANGE)
    service._comparator_mock._fetch_current_contest.return_value = {"id": "existing-1"}
    contest = _contest()

    contest_id = service.apply_contest(contest)

    assert contest_id == "existing-1"
    client.contests.create.assert_not_called()


def test_apply_contest_creates_team_group_for_scoreboard(service, client):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.CREATE)
    contest = _contest(shortname="finals")

    service.apply_contest(contest)

    client.groups.create_for_contest.assert_called_once()
    kwargs = client.groups.create_for_contest.call_args.kwargs
    assert kwargs["group_id"] == "finals-teams"
    assert "FINALS" in kwargs["name"]


def test_apply_contest_invokes_problem_and_team_services(service):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.CREATE)
    problems = ["p1", "p2"]
    teams = ["t1", "t2", "t3"]

    service.apply_contest(_contest(problems=problems, teams=teams))

    service._problem_mock.create_many.assert_called_once()
    service._team_mock.create_many.assert_called_once()
    assert service._problem_mock.create_many.call_args.args[0] == problems
    assert service._team_mock.create_many.call_args.args[0] == teams


def test_apply_contest_raises_when_problems_fail(service):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.CREATE)
    service._problem_mock.get_summary.return_value = {"failed": 2, "succeeded": 1}

    with pytest.raises(ContestError) as exc_info:
        service.apply_contest(_contest())
    assert "fail" in str(exc_info.value).lower()


def test_apply_contest_raises_when_teams_fail(service):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.CREATE)
    service._team_mock.get_summary.return_value = {"failed": 1, "succeeded": 0}

    with pytest.raises(ContestError):
        service.apply_contest(_contest())


def test_apply_contest_wraps_create_error_as_contest_error(service, client):
    service._comparator_mock.compare_contest.return_value = _change_set(ChangeType.CREATE)
    client.contests.create.side_effect = RuntimeError("upstream 500")

    with pytest.raises(ContestError) as exc_info:
        service.apply_contest(_contest())
    assert "upstream 500" in str(exc_info.value)


# ---------------------------------------------------------------- apply_contests entrypoint


def test_apply_contests_iterates_over_all_contests(secrets):
    config = MagicMock()
    config.infra = MagicMock()
    config.contests = [_contest("A"), _contest("B"), _contest("C")]

    with (
        patch("dom.core.services.contest.apply.APIClientFactory") as factory_cls,
        patch("dom.core.services.contest.apply.ContestApplicationService") as service_cls,
    ):
        instance = MagicMock()
        service_cls.return_value = instance
        factory_cls.return_value.create_admin_client.return_value = MagicMock()

        apply_contests(config, secrets)

    assert instance.apply_contest.call_count == 3
