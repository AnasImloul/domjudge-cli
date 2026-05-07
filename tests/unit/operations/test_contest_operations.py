"""Tests for contest operations: apply, plan_changes, load_config, verify."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from dom.core.operations import Context, run
from dom.core.operations.contest.apply import apply_contests_op
from dom.core.operations.contest.load_config import load_config_op
from dom.core.operations.contest.load_contest_config import load_contest_config_op
from dom.core.operations.contest.plan_changes import plan_contest_changes_op
from dom.core.operations.contest.verify_problemset import verify_problemset_op
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    return Context(secrets=MagicMock(spec=SecretsProvider))


def _make_dom_config(num_contests: int = 1, problems: int = 2, teams: int = 3):
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


def _result(shortname="C0", skipped=()):
    from dom.core.services.contest.apply import ContestApplyResult

    return ContestApplyResult(
        contest_shortname=shortname,
        contest_id=f"id-{shortname}",
        skipped_field_changes=list(skipped),
    )


def test_apply_runs_service_and_returns_results(context):
    config = _make_dom_config()
    with patch(
        "dom.core.operations.contest.apply._apply_all",
        return_value=[_result("C0")],
    ) as svc:
        result = run(apply_contests_op(config), context)
    svc.assert_called_once_with(config, context)
    assert len(result) == 1
    assert result[0].contest_shortname == "C0"


def test_apply_rejects_empty_contests(context):
    config = _make_dom_config(num_contests=0)
    with pytest.raises(typer.Exit):
        run(apply_contests_op(config), context)


def test_apply_summary_for_single_contest(context, capsys):
    config = _make_dom_config(num_contests=1)
    with patch(
        "dom.core.operations.contest.apply._apply_all",
        return_value=[_result("C0")],
    ):
        run(apply_contests_op(config), context)
    out = capsys.readouterr().out
    assert "C0" in out


def test_apply_summary_for_multiple_contests(context, capsys):
    config = _make_dom_config(num_contests=2)
    with patch(
        "dom.core.operations.contest.apply._apply_all",
        return_value=[_result("C0"), _result("C1")],
    ):
        run(apply_contests_op(config), context)
    out = capsys.readouterr().out
    assert "2 contests" in out


def test_apply_summary_flags_skipped_field_changes(context, capsys):
    from dom.core.services.contest.changes import FieldChange

    config = _make_dom_config(num_contests=1)
    skipped = [FieldChange(field="duration", old_value="5:00", new_value="6:00")]
    with patch(
        "dom.core.operations.contest.apply._apply_all",
        return_value=[_result("C0", skipped=skipped)],
    ):
        run(apply_contests_op(config), context)
    out = capsys.readouterr().out
    assert "skipped" in out


# ---------------------------------------------------------------- PlanChanges


def test_plan_returns_per_contest_change_sets(context):
    config = _make_dom_config(num_contests=2)
    fake_change = MagicMock(has_changes=True)

    with (
        patch("dom.core.operations.contest.plan_changes.wire_admin_api"),
        patch("dom.core.operations.contest.plan_changes.ContestStateComparator") as comparator_cls,
    ):
        comparator_cls.return_value.compare_contest.return_value = fake_change
        result = run(plan_contest_changes_op(config), context)

    assert len(result) == 2
    assert all(item["change_set"] is fake_change for item in result)


def test_plan_summary_counts_changes(context, capsys):
    config = _make_dom_config(num_contests=2)
    changes = [MagicMock(has_changes=True), MagicMock(has_changes=False)]

    with (
        patch("dom.core.operations.contest.plan_changes.wire_admin_api"),
        patch("dom.core.operations.contest.plan_changes.ContestStateComparator") as comparator_cls,
    ):
        comparator_cls.return_value.compare_contest.side_effect = changes
        run(plan_contest_changes_op(config), context)

    assert "1 with changes" in capsys.readouterr().out


def test_render_planned_changes_handles_no_changes(capsys):
    from dom.cli.contest.render import render_planned_changes

    render_planned_changes([])
    output = capsys.readouterr().out
    assert "No changes" in output


def test_render_planned_changes_renders_creates(capsys):
    from dom.cli.contest.render import render_planned_changes
    from dom.core.services.contest.changes import ChangeType

    change_set = MagicMock(
        change_type=ChangeType.CREATE,
        field_changes=[],
        resource_changes=[],
    )
    change_set.summary_parts.return_value = (ChangeType.CREATE, "C0", [])

    render_planned_changes([{"shortname": "C0", "change_set": change_set}])
    output = capsys.readouterr().out
    assert "Planned Changes" in output
    assert "C0" in output
    assert "CAN be applied" in output


# ---------------------------------------------------------------- LoadConfig


def test_load_config_rejects_missing_file(context, tmp_path):
    missing = tmp_path / "does-not-exist.yaml"
    with pytest.raises(typer.Exit):
        run(load_config_op(missing), context)


def test_load_config_passes_when_no_path(context):
    expected = MagicMock()
    expected.contests = []
    with patch(
        "dom.core.operations.contest.load_config.load_config", return_value=expected
    ) as loader:
        result = run(load_config_op(None), context)
    loader.assert_called_once_with(None, context.secrets)
    assert result is expected


def test_load_config_delegates_to_loader(context, tmp_path):
    cfg = tmp_path / "dom.yaml"
    cfg.write_text("infra: {port: 8080, judges: 1}\n")
    expected = MagicMock()
    expected.contests = []

    with patch(
        "dom.core.operations.contest.load_config.load_config", return_value=expected
    ) as loader:
        result = run(load_config_op(cfg), context)

    loader.assert_called_once_with(cfg, context.secrets)
    assert result is expected


def test_load_config_failure_propagates_as_exit(context):
    with patch(
        "dom.core.operations.contest.load_config.load_config",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(typer.Exit):
            run(load_config_op(None), context)


def test_load_config_summary_for_single_contest(context, capsys):
    config = _make_dom_config(num_contests=1, problems=5, teams=7)
    with patch("dom.core.operations.contest.load_config.load_config", return_value=config):
        run(load_config_op(None), context)
    out = capsys.readouterr().out
    assert "C0" in out
    assert "5 problems" in out


# ---------------------------------------------------------------- LoadContestConfig


def test_load_contest_delegates_with_name(context, tmp_path):
    cfg = tmp_path / "x.yaml"
    cfg.touch()
    expected = MagicMock()
    with patch(
        "dom.core.operations.contest.load_contest_config.load_contest_config",
        return_value=expected,
    ) as loader:
        result = run(load_contest_config_op(cfg, "ContestA"), context)
    loader.assert_called_once_with(cfg, "ContestA", context.secrets)
    assert result is expected


def test_load_contest_failure_propagates(context):
    with patch(
        "dom.core.operations.contest.load_contest_config.load_contest_config",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(typer.Exit):
            run(load_contest_config_op(None, "ContestA"), context)


# ---------------------------------------------------------------- VerifyProblemset


def test_verify_loads_and_delegates_to_service(context, tmp_path):
    contest = MagicMock(problems=[1, 2])
    infra = MagicMock()
    client = MagicMock()
    contest_path = tmp_path / "c.yaml"
    contest_path.touch()
    infra_path = tmp_path / "i.yaml"
    infra_path.touch()

    with (
        patch(
            "dom.core.operations.contest.verify_problemset.load_contest_config",
            return_value=contest,
        ) as load_contest,
        patch(
            "dom.core.operations.contest.verify_problemset.load_infrastructure_config",
            return_value=infra,
        ) as load_infra,
        patch("dom.core.operations.contest.verify_problemset.wire_admin_api") as wire,
        patch("dom.core.operations.contest.verify_problemset.verify_problemset") as verify,
    ):
        wire.return_value = client
        result = run(verify_problemset_op(contest_path, "ContestA", infra_path), context)

    load_contest.assert_called_once_with(contest_path, "ContestA", context.secrets)
    load_infra.assert_called_once_with(infra_path)
    wire.assert_called_once_with(infra, context.secrets)
    verify.assert_called_once_with(client=client, contest=contest, secrets=context.secrets)
    assert result is contest


def test_verify_rejects_missing_files(context, tmp_path):
    missing_contest = tmp_path / "c.yaml"
    missing_infra = tmp_path / "i.yaml"
    with pytest.raises(typer.Exit):
        run(verify_problemset_op(missing_contest, "ContestA", missing_infra), context)


def test_apply_op_is_single_step_with_summary_callback(context):
    """apply_contests_op is a single-step op returning ContestApplyResult list."""
    config = _make_dom_config()
    op = apply_contests_op(config)
    assert op.summary is not None
    # Single-step ops auto-wrap their return; show_progress is disabled.
    assert op.show_progress is False
