"""Tests for destroy, check_status, and print_status infrastructure operations."""

from unittest.mock import MagicMock, patch

import pytest

from dom.core.operations import Context, run
from dom.core.operations.infrastructure.check_status import check_infra_status_op
from dom.core.operations.infrastructure.destroy import destroy_infrastructure_op
from dom.core.operations.infrastructure.print_status import print_infra_status_op
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


# ---------------------------------------------------------------- Print status


def test_print_status_calls_human_presenter_by_default(context):
    fake_status = _make_status(docker_available=True)
    fake_status.services["domserver"] = ServiceStatus.HEALTHY

    with (
        patch("dom.core.operations.infrastructure.print_status.InfraService") as svc_cls,
        patch(
            "dom.core.operations.infrastructure.print_status._print_status_human_readable"
        ) as human,
        patch("dom.core.operations.infrastructure.print_status._print_status_json") as as_json,
    ):
        svc_cls.return_value.check_status.return_value = fake_status
        run(print_infra_status_op(json_output=False), context)

    human.assert_called_once_with(fake_status)
    as_json.assert_not_called()


def test_print_status_calls_json_presenter_when_requested(context):
    fake_status = _make_status(docker_available=True)

    with (
        patch("dom.core.operations.infrastructure.print_status.InfraService") as svc_cls,
        patch(
            "dom.core.operations.infrastructure.print_status._print_status_human_readable"
        ) as human,
        patch("dom.core.operations.infrastructure.print_status._print_status_json") as as_json,
    ):
        svc_cls.return_value.check_status.return_value = fake_status
        run(print_infra_status_op(json_output=True), context)

    as_json.assert_called_once_with(fake_status)
    human.assert_not_called()


def test_print_status_returns_status_value(context):
    fake_status = _make_status(docker_available=True)
    with (
        patch("dom.core.operations.infrastructure.print_status.InfraService") as svc_cls,
        patch("dom.core.operations.infrastructure.print_status._print_status_human_readable"),
    ):
        svc_cls.return_value.check_status.return_value = fake_status
        result = run(print_infra_status_op(), context)
    assert result is fake_status
