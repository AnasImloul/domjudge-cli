"""Tests for destroy, check_status, and print_status infrastructure operations."""

from unittest.mock import MagicMock, patch

import pytest

from dom.core.operations.base import OperationContext
from dom.core.operations.infrastructure.check_status import (
    CheckInfrastructureStatusOperation,
)
from dom.core.operations.infrastructure.destroy import (
    DestroyInfrastructureOperation,
    DestroyInfrastructureStep,
)
from dom.core.operations.infrastructure.print_status import (
    PrintInfrastructureStatusOperation,
)
from dom.types.infra import InfrastructureStatus, ServiceStatus
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    return OperationContext(secrets=MagicMock(spec=SecretsProvider))


def _make_status(docker_available: bool = True) -> InfrastructureStatus:
    status = InfrastructureStatus()
    status.docker_available = docker_available
    return status


# ---------------------------------------------------------------- Destroy


def test_destroy_step_delegates_with_remove_volumes_flag(context):
    with patch("dom.core.operations.infrastructure.destroy.InfraService") as cls:
        instance = MagicMock()
        cls.return_value = instance
        DestroyInfrastructureStep(remove_volumes=True).execute(context)
        instance.destroy.assert_called_once_with(remove_volumes=True)


def test_destroy_step_label_reflects_volume_removal():
    label_keep = DestroyInfrastructureStep(remove_volumes=False).description
    label_wipe = DestroyInfrastructureStep(remove_volumes=True).description
    assert "Stop" in label_keep
    assert "PERMANENT" in label_wipe


def test_destroy_operation_single_step():
    op = DestroyInfrastructureOperation(remove_volumes=True)
    steps = op.define_steps()
    assert len(steps) == 1
    assert steps[0].name == "destroy"


def test_destroy_build_result_messages(context):
    keep = DestroyInfrastructureOperation(remove_volumes=False)._build_result({}, context)
    wipe = DestroyInfrastructureOperation(remove_volumes=True)._build_result({}, context)
    assert "preserved" in keep.message.lower()
    assert "deleted" in wipe.message.lower()


# ---------------------------------------------------------------- Check status


def test_check_status_operation_single_step():
    steps = CheckInfrastructureStatusOperation().define_steps()
    assert [s.name for s in steps] == ["check"]


def test_check_status_step_returns_service_result(context):
    fake_status = _make_status(docker_available=True)
    with patch("dom.core.operations.infrastructure.check_status.InfraService") as cls:
        cls.return_value.check_status.return_value = fake_status
        op = CheckInfrastructureStatusOperation()
        result = op.execute(context)
    assert result.is_success()
    assert result.data is fake_status


def test_check_status_build_result_healthy_message(context):
    healthy = _make_status(docker_available=True)
    healthy.services["domserver"] = ServiceStatus.HEALTHY
    healthy.services["mariadb"] = ServiceStatus.HEALTHY
    op = CheckInfrastructureStatusOperation()
    result = op._build_result({"check": healthy}, context)
    assert result.is_success()
    assert "healthy" in result.message.lower()


def test_check_status_build_result_unhealthy_message(context):
    unhealthy = _make_status(docker_available=True)
    unhealthy.services["domserver"] = ServiceStatus.STOPPED
    op = CheckInfrastructureStatusOperation()
    result = op._build_result({"check": unhealthy}, context)
    assert result.is_success()
    assert "issues" in result.message.lower()


def test_check_status_build_result_failure_when_no_status(context):
    op = CheckInfrastructureStatusOperation()
    result = op._build_result({}, context)
    assert result.is_failure()


# ---------------------------------------------------------------- Print status


def test_print_status_operation_single_step():
    steps = PrintInfrastructureStatusOperation().define_steps()
    assert [s.name for s in steps] == ["check"]


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
        op = PrintInfrastructureStatusOperation(json_output=False)
        op.execute(context)
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
        op = PrintInfrastructureStatusOperation(json_output=True)
        op.execute(context)
        as_json.assert_called_once_with(fake_status)
        human.assert_not_called()
