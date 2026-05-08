"""Tests for apply_infrastructure_op."""

from unittest.mock import MagicMock, patch

import pytest
import typer
from pydantic import SecretStr

from dom.core.operations import Context, Steps, run
from dom.core.operations.infrastructure.apply import apply_infrastructure_op
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider


@pytest.fixture
def context():
    return Context(secrets=MagicMock(spec=SecretsProvider))


@pytest.fixture
def config():
    return InfraConfig(port=8080, judges=2, password=SecretStr("admin-pw"))


@pytest.fixture
def mock_service():
    """Patch InfraService and yield the mocked instance."""
    with patch("dom.core.operations.infrastructure.apply.InfraService") as cls:
        instance = MagicMock()
        cls.return_value = instance
        yield instance


def test_steps_are_in_expected_order(context, config, mock_service):
    plan = apply_infrastructure_op(config).build(context)
    assert isinstance(plan, Steps)
    labels = [s.label for s in plan.steps]
    assert labels == [
        "Validate prerequisites",
        "Generate compose file",
        "Start MariaDB",
        "Start MySQL client",
        "Start DOMserver",
        "Wait for DOMserver to be healthy",
        "Fetch judgedaemon password",
        "Regenerate compose with real password",
        "Start 2 judgehost(s)",
        "Configure admin password",
    ]


def test_summary_includes_port_and_judge_count(context, config, mock_service):
    plan = apply_infrastructure_op(config).build(context)
    assert "8080" in plan.summary
    assert "2 judgehost" in plan.summary


def test_run_executes_full_pipeline_in_order(context, config, mock_service):
    mock_service.fetch_and_store_judge_password.return_value = "pw"
    run(apply_infrastructure_op(config), context)

    mock_service.validate_prerequisites.assert_called_once_with(8080)
    mock_service.generate_compose_bootstrap.assert_called_once_with(config)
    assert mock_service.start_service.call_count == 3  # mariadb, mysql-client, domserver
    mock_service.wait_domserver_healthy.assert_called_once()
    mock_service.fetch_and_store_judge_password.assert_called_once()
    mock_service.regenerate_compose.assert_called_once_with(config)
    mock_service.start_judgehosts.assert_called_once_with(2)
    mock_service.configure_admin_password.assert_called_once_with(config)


def test_failing_step_raises_typer_exit(context, config, mock_service):
    mock_service.start_service.side_effect = RuntimeError("docker daemon down")
    with pytest.raises(typer.Exit):
        run(apply_infrastructure_op(config), context)


def test_dry_run_does_not_call_service(context, config, mock_service):
    dry_ctx = Context(secrets=context.secrets, dry_run=True)
    run(apply_infrastructure_op(config), dry_ctx)
    mock_service.validate_prerequisites.assert_not_called()
    mock_service.start_service.assert_not_called()
