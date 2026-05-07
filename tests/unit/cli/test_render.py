"""Tests for CLI-side change-set renderers (Rich-markup formatting)."""

from pydantic import SecretStr

from dom.cli.contest.render import format_contest_change_summary
from dom.cli.infrastructure.render import format_change_summary
from dom.core.services.contest.changes import (
    ChangeType,
    ContestChangeSet,
    FieldChange,
    ResourceChange,
)
from dom.core.services.infra.state import InfraChangeSet, InfraChangeType
from dom.types.infra import InfraConfig


def _config(**kwargs) -> InfraConfig:
    base = {"port": 8080, "judges": 4, "password": SecretStr("test")}
    base.update(kwargs)
    return InfraConfig(**base)


# ---------------------------------------------------------------- infra renderer


def test_infra_summary_create():
    cs = InfraChangeSet(change_type=InfraChangeType.CREATE, old_config=None, new_config=_config())
    summary = format_change_summary(cs)
    assert "CREATE" in summary
    assert "new infrastructure" in summary


def test_infra_summary_no_change():
    cs = InfraChangeSet(
        change_type=InfraChangeType.NO_CHANGE,
        old_config=_config(),
        new_config=_config(),
    )
    assert "NO CHANGES" in format_change_summary(cs)


def test_infra_summary_scale_up():
    cs = InfraChangeSet(
        change_type=InfraChangeType.SCALE_JUDGES,
        old_config=_config(judges=4),
        new_config=_config(judges=8),
        judge_diff=4,
    )
    summary = format_change_summary(cs)
    assert "SCALE UP" in summary
    assert "4" in summary and "8" in summary
    assert "safe live change" in summary


def test_infra_summary_scale_down():
    cs = InfraChangeSet(
        change_type=InfraChangeType.SCALE_JUDGES,
        old_config=_config(judges=8),
        new_config=_config(judges=4),
        judge_diff=-4,
    )
    assert "SCALE DOWN" in format_change_summary(cs)


def test_infra_summary_port_change():
    cs = InfraChangeSet(
        change_type=InfraChangeType.PORT_CHANGE,
        old_config=_config(port=8080),
        new_config=_config(port=9090),
    )
    summary = format_change_summary(cs)
    assert "PORT CHANGE" in summary
    assert "8080" in summary and "9090" in summary
    assert "requires restart" in summary


def test_infra_summary_password_change():
    cs = InfraChangeSet(
        change_type=InfraChangeType.PASSWORD_CHANGE,
        old_config=_config(),
        new_config=_config(),
    )
    assert "PASSWORD CHANGE" in format_change_summary(cs)


def test_infra_summary_full_restart():
    cs = InfraChangeSet(
        change_type=InfraChangeType.FULL_RESTART,
        old_config=_config(),
        new_config=_config(),
    )
    assert "MULTIPLE CHANGES" in format_change_summary(cs)


# ---------------------------------------------------------------- contest renderer


def test_contest_summary_create():
    cs = ContestChangeSet(
        contest_shortname="test2025",
        change_type=ChangeType.CREATE,
        field_changes=[],
        resource_changes=[],
    )
    summary = format_contest_change_summary(cs)
    assert "CREATE" in summary
    assert "test2025" in summary


def test_contest_summary_update():
    cs = ContestChangeSet(
        contest_shortname="test2025",
        change_type=ChangeType.UPDATE,
        field_changes=[FieldChange("duration", "5:00:00", "6:00:00")],
        resource_changes=[ResourceChange("problems", ["problem-a"], [], [])],
    )
    summary = format_contest_change_summary(cs)
    assert "UPDATE" in summary
    assert "test2025" in summary


def test_contest_summary_no_change():
    cs = ContestChangeSet(
        contest_shortname="test2025",
        change_type=ChangeType.NO_CHANGE,
        field_changes=[],
        resource_changes=[],
    )
    summary = format_contest_change_summary(cs)
    assert "NO CHANGES" in summary
    assert "test2025" in summary
