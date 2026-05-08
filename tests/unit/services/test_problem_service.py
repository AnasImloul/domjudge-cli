"""Tests for ProblemService."""

from unittest.mock import MagicMock

import pytest

from dom.core.services.base import ServiceContext
from dom.core.services.problem.apply import ProblemService
from dom.exceptions import APIError, ProblemError


def _problem(name: str = "p1") -> MagicMock:
    """Build a stand-in for a ``ProblemPackage`` with the attrs the service reads."""
    pkg = MagicMock()
    pkg.yaml.name = name
    pkg.id = None
    return pkg


@pytest.fixture
def client():
    """Mock matching the DomJudgeAPIProtocol surface used by ProblemService."""
    return MagicMock()


@pytest.fixture
def service(client):
    return ProblemService(client)


@pytest.fixture
def context(client):
    return ServiceContext(client=client, contest_id="c1")


# ---------------------------------------------------------------- create


def test_create_returns_failure_when_contest_id_missing(service, client):
    ctx = ServiceContext(client=client)  # no contest_id
    result = service.create(_problem(), ctx)

    assert result.success is False
    assert isinstance(result.error, ValueError)
    client.problems.add_to_contest.assert_not_called()


def test_create_succeeds_and_assigns_returned_id(service, client, context):
    client.problems.add_to_contest.return_value = "remote-42"
    pkg = _problem("watermelon")

    result = service.create(pkg, context)

    assert result.success is True
    assert result.created is True
    assert result.data is pkg
    assert pkg.id == "remote-42"
    client.problems.add_to_contest.assert_called_once_with("c1", pkg)


def test_create_wraps_api_error_as_problem_error(service, client, context):
    client.problems.add_to_contest.side_effect = APIError("boom", status_code=500)

    result = service.create(_problem("bitwalker"), context)

    assert result.success is False
    assert isinstance(result.error, ProblemError)
    assert "bitwalker" in str(result.error)


def test_create_does_not_swallow_unexpected_exceptions(service, client, context):
    """Non-APIError surfaces — service only catches APIError on purpose."""
    client.problems.add_to_contest.side_effect = RuntimeError("network died")

    with pytest.raises(RuntimeError):
        service.create(_problem(), context)


# ---------------------------------------------------------------- create_many


def test_create_many_returns_one_result_per_input(service, client, context):
    client.problems.add_to_contest.side_effect = ["id-1", "id-2", "id-3"]

    results = service.create_many([_problem("a"), _problem("b"), _problem("c")], context)

    assert len(results) == 3
    assert all(r.success for r in results)
    assert client.problems.add_to_contest.call_count == 3


def test_create_many_collects_partial_failures(service, client, context):
    """A failing problem doesn't take down the others; it shows up as a failed result."""

    def fake_add(contest_id, pkg):
        if pkg.yaml.name == "broken":
            raise APIError("nope", status_code=400)
        return f"id-{pkg.yaml.name}"

    client.problems.add_to_contest.side_effect = fake_add

    results = service.create_many([_problem("a"), _problem("broken"), _problem("c")], context)

    assert len(results) == 3
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    assert len(successes) == 2
    assert len(failures) == 1
    assert isinstance(failures[0].error, ProblemError)


def test_create_many_summary_counts_match(service, client, context):
    client.problems.add_to_contest.side_effect = ["id-a", APIError("x", status_code=500), "id-c"]

    results = service.create_many([_problem("a"), _problem("b"), _problem("c")], context)
    summary = service.get_summary(results)

    assert summary["total"] == 3
    assert summary["successful"] == 2
    assert summary["failed"] == 1
    assert summary["created"] == 2
