"""Tests for contest operations: apply, plan_changes, load_config, verify."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dom.core.operations.base import OperationContext
from dom.core.operations.contest.apply import (
    ApplyAllContestsStep,
    ApplyContestsOperation,
)
from dom.core.operations.contest.load_config import LoadConfigOperation
from dom.core.operations.contest.load_contest_config import LoadContestConfigOperation
from dom.core.operations.contest.plan_changes import PlanContestChangesOperation
from dom.core.operations.contest.verify_problemset import VerifyProblemsetOperation
from dom.core.services.contest.changes import ChangeType
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    return OperationContext(secrets=MagicMock(spec=SecretsProvider))


def _make_dom_config(num_contests: int = 1, problems: int = 2, teams: int = 3):
    """Build a minimally-stubbed DomConfig that doesn't trigger pydantic validation."""
    contests = []
    for i in range(num_contests):
        contest = MagicMock()
        contest.shortname = f"C{i}"
        contest.problems = list(range(problems))
        contest.teams = list(range(teams))
        contests.append(contest)
    config = MagicMock()
    config.contests = contests
    config.infra = MagicMock()
    return config


# ---------------------------------------------------------------- ApplyContests


def test_apply_all_step_delegates_to_service(context):
    config = _make_dom_config()
    with patch("dom.core.operations.contest.apply.apply_contests") as svc:
        ApplyAllContestsStep(config).execute(context)
        svc.assert_called_once_with(config, context.secrets)


def test_apply_operation_single_step():
    config = _make_dom_config()
    steps = ApplyContestsOperation(config).define_steps()
    assert [s.name for s in steps] == ["apply"]


def test_apply_operation_validate_rejects_empty_contests(context):
    config = _make_dom_config(num_contests=0)
    errors = ApplyContestsOperation(config).validate(context)
    assert errors and "No contests" in errors[0]


def test_apply_operation_validate_passes_with_contests(context):
    config = _make_dom_config()
    assert ApplyContestsOperation(config).validate(context) == []


def test_apply_operation_message_single_contest(context):
    config = _make_dom_config(num_contests=1, problems=4, teams=10)
    result = ApplyContestsOperation(config)._build_result({}, context)
    assert result.is_success()
    assert "C0" in result.message
    assert "4 problems" in result.message
    assert "10 teams" in result.message


def test_apply_operation_message_multiple_contests(context):
    config = _make_dom_config(num_contests=2)
    result = ApplyContestsOperation(config)._build_result({}, context)
    assert "2 contests" in result.message
    assert "C0" in result.message
    assert "C1" in result.message


# ---------------------------------------------------------------- PlanChanges


def test_plan_run_returns_per_contest_change_sets(context):
    config = _make_dom_config(num_contests=2)
    fake_change = MagicMock(has_changes=True)

    with (
        patch("dom.core.operations.contest.plan_changes.APIClientFactory"),
        patch("dom.core.operations.contest.plan_changes.ContestStateComparator") as comparator_cls,
        patch("dom.core.operations.contest.plan_changes._print_planned_changes"),
    ):
        comparator_cls.return_value.compare_contest.return_value = fake_change
        result = PlanContestChangesOperation(config).run(context)

    assert len(result) == 2
    assert all(item["change_set"] is fake_change for item in result)


def test_plan_run_invokes_presenter(context):
    config = _make_dom_config()
    fake_change = MagicMock(has_changes=True)

    with (
        patch("dom.core.operations.contest.plan_changes.APIClientFactory"),
        patch("dom.core.operations.contest.plan_changes.ContestStateComparator") as comparator_cls,
        patch("dom.core.operations.contest.plan_changes._print_planned_changes") as presenter,
    ):
        comparator_cls.return_value.compare_contest.return_value = fake_change
        PlanContestChangesOperation(config).run(context)

    presenter.assert_called_once()


def test_plan_success_message_counts_changes():
    config = _make_dom_config()
    op = PlanContestChangesOperation(config)
    changes = [
        {"shortname": "C0", "change_set": MagicMock(has_changes=True)},
        {"shortname": "C1", "change_set": MagicMock(has_changes=False)},
    ]
    assert "1 with changes" in op._success_message(changes)


def test_plan_success_message_handles_empty():
    config = _make_dom_config()
    op = PlanContestChangesOperation(config)
    assert "0 with changes" in op._success_message([])


def test_plan_presenter_handles_no_changes(capsys):
    from dom.core.operations.contest.plan_changes import _print_planned_changes

    _print_planned_changes([])
    output = capsys.readouterr().out
    assert "No changes" in output


def test_plan_presenter_renders_creates(capsys):
    from dom.core.operations.contest.plan_changes import _print_planned_changes

    change_set = MagicMock(
        change_type=ChangeType.CREATE,
        field_changes=[],
        resource_changes=[],
    )
    change_set.summary.return_value = "[CREATE] Contest C0"

    _print_planned_changes([{"shortname": "C0", "change_set": change_set}])
    output = capsys.readouterr().out
    assert "Planned Changes" in output
    assert "C0" in output
    assert "CAN be applied" in output


# ---------------------------------------------------------------- LoadConfig


def test_load_config_validate_rejects_missing_file(context, tmp_path):
    missing = tmp_path / "does-not-exist.yaml"
    errors = LoadConfigOperation(missing).validate(context)
    assert errors and "not found" in errors[0]


def test_load_config_validate_passes_when_no_path(context):
    assert LoadConfigOperation(None).validate(context) == []


def test_load_config_run_delegates_to_loader(context, tmp_path):
    cfg = tmp_path / "dom.yaml"
    cfg.write_text("infra: {port: 8080, judges: 1}\n")
    expected = MagicMock()

    with patch(
        "dom.core.operations.contest.load_config.load_config", return_value=expected
    ) as loader:
        result = LoadConfigOperation(cfg).run(context)

    loader.assert_called_once_with(cfg, context.secrets)
    assert result is expected


def test_load_config_execute_failure_propagates(context):
    err = RuntimeError("boom")
    with patch("dom.core.operations.contest.load_config.load_config", side_effect=err):
        result = LoadConfigOperation(None).execute(context)
    assert result.is_failure()
    assert result.error is err


def test_load_config_success_message_for_single_contest():
    config = _make_dom_config(num_contests=1, problems=5, teams=7)
    msg = LoadConfigOperation(None)._success_message(config)
    assert "C0" in msg
    assert "5 problems" in msg


# ---------------------------------------------------------------- LoadContestConfig


def test_load_contest_run_delegates_with_name(context):
    expected = MagicMock()
    with patch(
        "dom.core.operations.contest.load_contest_config.load_contest_config",
        return_value=expected,
    ) as loader:
        result = LoadContestConfigOperation(Path("x.yaml"), "ContestA").run(context)
    loader.assert_called_once_with(Path("x.yaml"), "ContestA", context.secrets)
    assert result is expected


def test_load_contest_operation_describe_includes_contest_name():
    op = LoadContestConfigOperation(None, "ContestA")
    assert "ContestA" in op.describe()


def test_load_contest_execute_failure_propagates(context):
    err = RuntimeError("boom")
    with patch(
        "dom.core.operations.contest.load_contest_config.load_contest_config",
        side_effect=err,
    ):
        result = LoadContestConfigOperation(None, "ContestA").execute(context)
    assert result.is_failure()


# ---------------------------------------------------------------- VerifyProblemset


def test_verify_run_loads_and_delegates_to_service(context):
    contest = MagicMock(problems=[1, 2])
    infra = MagicMock()
    client = MagicMock()

    with (
        patch(
            "dom.core.operations.contest.verify_problemset.load_contest_config",
            return_value=contest,
        ) as load_contest,
        patch(
            "dom.core.operations.contest.verify_problemset.load_infrastructure_config",
            return_value=infra,
        ) as load_infra,
        patch("dom.core.operations.contest.verify_problemset.APIClientFactory") as factory_cls,
        patch("dom.core.operations.contest.verify_problemset.verify_problemset") as verify,
    ):
        factory_cls.return_value.create_admin_client.return_value = client
        result = VerifyProblemsetOperation(Path("c.yaml"), "ContestA", Path("i.yaml")).run(context)

    load_contest.assert_called_once_with(Path("c.yaml"), "ContestA", context.secrets)
    load_infra.assert_called_once_with(Path("i.yaml"))
    factory_cls.return_value.create_admin_client.assert_called_once_with(infra, context.secrets)
    verify.assert_called_once_with(client=client, contest=contest, secrets=context.secrets)
    assert result is contest


def test_verify_validate_rejects_missing_files(context, tmp_path):
    missing_contest = tmp_path / "c.yaml"
    missing_infra = tmp_path / "i.yaml"
    op = VerifyProblemsetOperation(missing_contest, "ContestA", missing_infra)
    errors = op.validate(context)
    assert any("not found" in e for e in errors)
    assert len(errors) == 2


def test_verify_success_message_includes_problem_count():
    contest = MagicMock(problems=[1, 2, 3, 4])
    op = VerifyProblemsetOperation(None, "ContestA")
    assert "4 problems" in op._success_message(contest)
