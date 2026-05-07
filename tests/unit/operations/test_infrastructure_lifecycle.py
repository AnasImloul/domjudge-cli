"""Tests for destroy, check_status infrastructure operations and the status renderer."""

from unittest.mock import MagicMock, patch

import pytest

from dom.core.operations import Context, run
from dom.core.operations.infrastructure.check_status import check_infra_status_op
from dom.core.operations.infrastructure.destroy import destroy_infrastructure_op
from dom.types.infra import InfrastructureStatus, ServiceStatus
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    return Context(secrets=MagicMock(spec=SecretsProvider))


def _make_status(docker_available: bool = True) -> InfrastructureStatus:
    status = InfrastructureStatus()
    status.docker_available = docker_available
    return status


# ---------------------------------------------------------------- Destroy


def test_destroy_calls_service_with_remove_volumes_flag(context):
    with patch("dom.core.operations.infrastructure.destroy.InfraService") as cls:
        instance = MagicMock()
        cls.return_value = instance
        run(destroy_infrastructure_op(remove_volumes=True), context)
        instance.destroy.assert_called_once_with(remove_volumes=True)


def test_destroy_step_label_reflects_volume_removal(context):
    with patch("dom.core.operations.infrastructure.destroy.InfraService"):
        plan_keep = destroy_infrastructure_op(remove_volumes=False).build(context)
        plan_wipe = destroy_infrastructure_op(remove_volumes=True).build(context)
    assert "Stop" in plan_keep.steps[0].label
    assert "PERMANENT" in plan_wipe.steps[0].label


def test_destroy_summary_messages(context):
    with patch("dom.core.operations.infrastructure.destroy.InfraService"):
        plan_keep = destroy_infrastructure_op(remove_volumes=False).build(context)
        plan_wipe = destroy_infrastructure_op(remove_volumes=True).build(context)
    assert "preserved" in plan_keep.summary.lower()
    assert "deleted" in plan_wipe.summary.lower()


# ---------------------------------------------------------------- Check status


def test_check_status_returns_service_result(context):
    fake_status = _make_status(docker_available=True)
    with patch("dom.core.operations.infrastructure.check_status.InfraService") as cls:
        cls.return_value.check_status.return_value = fake_status
        result = run(check_infra_status_op(), context)
    assert result is fake_status


def test_check_status_summary_for_healthy(context, capsys):
    healthy = _make_status(docker_available=True)
    healthy.services["domserver"] = ServiceStatus.HEALTHY
    healthy.services["mariadb"] = ServiceStatus.HEALTHY
    with patch("dom.core.operations.infrastructure.check_status.InfraService") as cls:
        cls.return_value.check_status.return_value = healthy
        run(check_infra_status_op(), context)
    assert "healthy" in capsys.readouterr().out.lower()


def test_check_status_summary_for_unhealthy(context, capsys):
    unhealthy = _make_status(docker_available=True)
    unhealthy.services["domserver"] = ServiceStatus.STOPPED
    with patch("dom.core.operations.infrastructure.check_status.InfraService") as cls:
        cls.return_value.check_status.return_value = unhealthy
        run(check_infra_status_op(), context)
    assert "issues" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------- Status renderer (CLI layer)


def test_render_status_human_readable_prints_to_console(capsys):
    from dom.cli.infrastructure.render import render_status

    status = _make_status(docker_available=True)
    status.services["domserver"] = ServiceStatus.HEALTHY

    render_status(status, json_output=False)
    out = capsys.readouterr().out
    assert "HEALTHY" in out
    assert "domserver" in out


def test_render_status_json_emits_valid_json(capsys):
    import json as _json

    from dom.cli.infrastructure.render import render_status

    status = _make_status(docker_available=True)
    status.services["domserver"] = ServiceStatus.HEALTHY

    render_status(status, json_output=True)
    out = capsys.readouterr().out.strip()
    parsed = _json.loads(out)
    assert parsed["docker_available"] is True


def test_render_status_handles_unavailable_docker(capsys):
    from dom.cli.infrastructure.render import render_status

    status = _make_status(docker_available=False)
    status.docker_error = "daemon down"

    render_status(status)
    out = capsys.readouterr().out
    assert "Not available" in out
    assert "daemon down" in out
