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
from dom.core.services.contest.changes import (
    ChangeType,
    ContestChangeSet,
    ContestPlan,
    ContestPlanItem,
)
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


def _stub_service(skipped_per_contest: dict[str, list] | None = None):
    """Service stub whose toolkit methods record per-contest state.

    Returns ``(svc, calls)`` where ``calls`` is the per-method invocation log.
    """
    skipped_per_contest = skipped_per_contest or {}
    svc = MagicMock()
    svc.client = MagicMock()
    svc.compare.side_effect = lambda contest: ContestChangeSet(
        contest_shortname=contest.shortname,
        change_type=ChangeType.CREATE,
        field_changes=[],
        resource_changes=[],
    )
    svc.resolve_or_create.side_effect = lambda contest, _cs: (
        f"id-{contest.shortname}",
        skipped_per_contest.get(contest.shortname, []),
    )
    svc.provision_team_group.side_effect = lambda contest_id, _sn: f"group-{contest_id}"
    svc.apply_problems.return_value = None
    svc.apply_teams.return_value = None
    return svc


def test_apply_runs_five_steps_per_contest(context):
    config = _make_dom_config(num_contests=2)
    svc = _stub_service()
    with (
        patch("dom.core.operations.contest.apply.wire_admin_api"),
        patch("dom.core.operations.contest.apply.ContestApplicationService", return_value=svc),
        patch("dom.core.operations.contest.apply.ProblemService"),
        patch("dom.core.operations.contest.apply.TeamService"),
    ):
        results = run(apply_contests_op(config), context)

    assert svc.compare.call_count == 2
    assert svc.resolve_or_create.call_count == 2
    assert svc.provision_team_group.call_count == 2
    assert svc.apply_problems.call_count == 2
    assert svc.apply_teams.call_count == 2
    assert [r.contest_shortname for r in results] == ["C0", "C1"]
    assert [r.contest_id for r in results] == ["id-C0", "id-C1"]


def test_apply_rejects_empty_contests(context):
    config = _make_dom_config(num_contests=0)
    with pytest.raises(typer.Exit):
        run(apply_contests_op(config), context)


def test_apply_summary_for_single_contest(context, capsys):
    config = _make_dom_config(num_contests=1)
    with (
        patch("dom.core.operations.contest.apply.wire_admin_api"),
        patch(
            "dom.core.operations.contest.apply.ContestApplicationService",
            return_value=_stub_service(),
        ),
        patch("dom.core.operations.contest.apply.ProblemService"),
        patch("dom.core.operations.contest.apply.TeamService"),
    ):
        run(apply_contests_op(config), context)
    out = capsys.readouterr().out
    assert "C0" in out
    assert "Applied" in out


def test_apply_summary_for_multiple_contests(context, capsys):
    config = _make_dom_config(num_contests=2)
    with (
        patch("dom.core.operations.contest.apply.wire_admin_api"),
        patch(
            "dom.core.operations.contest.apply.ContestApplicationService",
            return_value=_stub_service(),
        ),
        patch("dom.core.operations.contest.apply.ProblemService"),
        patch("dom.core.operations.contest.apply.TeamService"),
    ):
        run(apply_contests_op(config), context)
    out = capsys.readouterr().out
    assert "2 contests" in out


def test_apply_summary_flags_skipped_field_changes(context, capsys):
    from dom.core.services.contest.changes import FieldChange

    config = _make_dom_config(num_contests=1)
    skipped = [FieldChange(field="duration", old_value="5:00", new_value="6:00")]
    with (
        patch("dom.core.operations.contest.apply.wire_admin_api"),
        patch(
            "dom.core.operations.contest.apply.ContestApplicationService",
            return_value=_stub_service(skipped_per_contest={"C0": skipped}),
        ),
        patch("dom.core.operations.contest.apply.ProblemService"),
        patch("dom.core.operations.contest.apply.TeamService"),
    ):
        run(apply_contests_op(config), context)
    out = capsys.readouterr().out
    assert "skipped" in out


def test_apply_op_is_multi_step_with_summary_callback(context):
    """apply_contests_op now returns Steps; framework forwards the result."""
    config = _make_dom_config()
    op = apply_contests_op(config)
    assert op.summary is not None
    assert op.show_progress is True


# ---------------------------------------------------------------- PlanChanges


def test_plan_returns_typed_plan_with_one_item_per_contest(context):
    config = _make_dom_config(num_contests=2)
    fake_change = ContestChangeSet(
        contest_shortname="C",
        change_type=ChangeType.CREATE,
        field_changes=[],
        resource_changes=[],
    )

    with (
        patch("dom.core.operations.contest.plan_changes.wire_admin_api"),
        patch("dom.core.operations.contest.plan_changes.ContestStateComparator") as comparator_cls,
    ):
        comparator_cls.return_value.compare_contest.return_value = fake_change
        result = run(plan_contest_changes_op(config), context)

    assert isinstance(result, ContestPlan)
    assert len(result.items) == 2
    assert all(isinstance(item, ContestPlanItem) for item in result.items)
    assert all(item.change_set is fake_change for item in result.items)


def test_plan_summary_counts_changes(context, capsys):
    config = _make_dom_config(num_contests=2)
    changes = [
        ContestChangeSet(
            contest_shortname="C0",
            change_type=ChangeType.CREATE,
            field_changes=[],
            resource_changes=[],
        ),
        ContestChangeSet(
            contest_shortname="C1",
            change_type=ChangeType.NO_CHANGE,
            field_changes=[],
            resource_changes=[],
        ),
    ]

    with (
        patch("dom.core.operations.contest.plan_changes.wire_admin_api"),
        patch("dom.core.operations.contest.plan_changes.ContestStateComparator") as comparator_cls,
    ):
        comparator_cls.return_value.compare_contest.side_effect = changes
        run(plan_contest_changes_op(config), context)

    assert "1 with changes" in capsys.readouterr().out


def test_render_planned_changes_handles_empty_plan(capsys):
    from dom.cli.contest.render import render_planned_changes

    render_planned_changes(ContestPlan())
    output = capsys.readouterr().out
    assert "No changes" in output


def test_render_planned_changes_renders_creates(capsys):
    from dom.cli.contest.render import render_planned_changes

    cs = ContestChangeSet(
        contest_shortname="C0",
        change_type=ChangeType.CREATE,
        field_changes=[],
        resource_changes=[],
    )
    plan = ContestPlan(items=[ContestPlanItem(shortname="C0", change_set=cs)])

    render_planned_changes(plan)
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
