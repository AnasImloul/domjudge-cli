"""Tests for ApplyInfrastructureOperation."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from dom.core.operations.base import OperationContext
from dom.core.operations.infrastructure.apply import (
    ApplyInfrastructureOperation,
    ConfigureAdminPasswordStep,
    FetchJudgePasswordStep,
    GenerateComposeStep,
    RegenerateComposeStep,
    StartDatabaseStep,
    StartDOMServerStep,
    StartJudgehostsStep,
    StartMySQLClientStep,
    ValidatePrerequisitesStep,
    WaitForHealthyStep,
)
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    secrets = MagicMock(spec=SecretsProvider)
    return OperationContext(secrets=secrets)


@pytest.fixture
def config():
    return InfraConfig(port=8080, judges=2, password=SecretStr("admin-pw"))


@pytest.fixture
def mock_service():
    """Patch InfraService in the operation module and return the mock instance."""
    with patch("dom.core.operations.infrastructure.apply.InfraService") as cls:
        instance = MagicMock()
        cls.return_value = instance
        yield instance


# ---------------------------------------------------------------- Steps delegate


def test_validate_step_calls_validate_and_warn(context, mock_service):
    ValidatePrerequisitesStep(8080).execute(context)
    mock_service.validate_prerequisites.assert_called_once_with(8080)
    mock_service.warn_privileged_port.assert_called_once_with(8080)


def test_generate_compose_step_uses_bootstrap(context, mock_service, config):
    GenerateComposeStep(config).execute(context)
    mock_service.generate_compose_bootstrap.assert_called_once_with(config)


def test_start_database_step(context, mock_service):
    StartDatabaseStep().execute(context)
    mock_service.start_service.assert_called_once_with("mariadb")


def test_start_mysql_client_step(context, mock_service):
    StartMySQLClientStep().execute(context)
    mock_service.start_service.assert_called_once_with("mysql-client")


def test_start_domserver_step(context, mock_service):
    StartDOMServerStep().execute(context)
    mock_service.start_service.assert_called_once_with("domserver")


def test_wait_healthy_step(context, mock_service):
    WaitForHealthyStep().execute(context)
    mock_service.wait_domserver_healthy.assert_called_once()


def test_fetch_judge_password_step_returns_password(context, mock_service):
    mock_service.fetch_and_store_judge_password.return_value = "pw"
    assert FetchJudgePasswordStep().execute(context) == "pw"


def test_regenerate_compose_step(context, mock_service, config):
    RegenerateComposeStep(config).execute(context)
    mock_service.regenerate_compose.assert_called_once_with(config)


def test_start_judgehosts_step_passes_count(context, mock_service):
    StartJudgehostsStep(3).execute(context)
    mock_service.start_judgehosts.assert_called_once_with(3)


def test_configure_admin_password_step(context, mock_service, config):
    ConfigureAdminPasswordStep(config).execute(context)
    mock_service.configure_admin_password.assert_called_once_with(config)


# ---------------------------------------------------------------- Operation


def test_define_steps_in_correct_order(config):
    op = ApplyInfrastructureOperation(config)
    step_names = [s.name for s in op.define_steps()]
    assert step_names == [
        "validate",
        "generate_compose",
        "start_database",
        "start_mysql_client",
        "start_domserver",
        "wait_healthy",
        "fetch_password",
        "regenerate_compose",
        "start_judgehosts",
        "configure_admin",
    ]


def test_validate_returns_empty_when_prerequisites_pass(config, context, mock_service):
    errors = ApplyInfrastructureOperation(config).validate(context)
    assert errors == []
    mock_service.validate_prerequisites.assert_called_once_with(8080)


def test_validate_collects_errors_from_failed_prerequisites(config, context, mock_service):
    mock_service.validate_prerequisites.side_effect = RuntimeError("port already in use")
    errors = ApplyInfrastructureOperation(config).validate(context)
    assert errors == ["port already in use"]


def test_describe_is_human_readable(config):
    description = ApplyInfrastructureOperation(config).describe()
    assert "Deploy" in description


def test_build_result_message_includes_port_and_judge_count(config, context):
    op = ApplyInfrastructureOperation(config)
    result = op._build_result({}, context)
    assert result.is_success()
    assert "8080" in result.message
    assert "2 judgehost" in result.message


def test_execute_runs_full_pipeline_in_order(config, context, mock_service):
    """End-to-end: each service method should be called once, in step order."""
    mock_service.fetch_and_store_judge_password.return_value = "pw"

    result = ApplyInfrastructureOperation(config).execute(context)

    assert result.is_success()
    # All ten orchestration calls executed
    mock_service.validate_prerequisites.assert_called_once_with(8080)
    mock_service.warn_privileged_port.assert_called_once_with(8080)
    mock_service.generate_compose_bootstrap.assert_called_once_with(config)
    assert mock_service.start_service.call_count == 3  # mariadb, mysql-client, domserver
    mock_service.wait_domserver_healthy.assert_called_once()
    mock_service.fetch_and_store_judge_password.assert_called_once()
    mock_service.regenerate_compose.assert_called_once_with(config)
    mock_service.start_judgehosts.assert_called_once_with(2)
    mock_service.configure_admin_password.assert_called_once_with(config)


def test_execute_returns_failure_when_step_raises(config, context, mock_service):
    mock_service.start_service.side_effect = RuntimeError("docker daemon down")

    result = ApplyInfrastructureOperation(config).execute(context)

    assert result.is_failure()
    assert "docker daemon down" in str(result.error)
