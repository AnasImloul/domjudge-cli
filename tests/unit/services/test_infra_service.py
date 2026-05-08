"""Tests for InfraService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from dom.core.services.infra.service import InfraService
from dom.types.infra import InfraConfig, ServiceStatus
from dom.types.secrets import SecretsProvider


@pytest.fixture
def secrets():
    return MagicMock(spec=SecretsProvider)


@pytest.fixture
def service(temp_dir, secrets):
    """InfraService with stubbed Docker and filesystem dependencies."""
    with (
        patch("dom.core.services.infra.service.DockerClient") as docker_cls,
        patch("dom.core.services.infra.service.ensure_dom_directory", return_value=temp_dir),
    ):
        docker = MagicMock()
        docker._cmd = ["docker"]
        docker_cls.return_value = docker
        svc = InfraService(secrets)
        svc._docker_mock = docker  # type: ignore[attr-defined]
        yield svc


@pytest.fixture
def config():
    return InfraConfig(port=8080, judges=2, password=SecretStr("admin-pass"))


# ---------------------------------------------------------------- Validation


def test_validate_prerequisites_delegates_to_util(service):
    with patch("dom.core.services.infra.service.validate_infrastructure_prerequisites") as v:
        service.validate_prerequisites(8080)
        v.assert_called_once_with(8080)


# ---------------------------------------------------------------- Compose


def test_generate_compose_bootstrap_uses_placeholder_password(service, secrets, config):
    with patch("dom.core.services.infra.service.generate_docker_compose") as gen:
        service.generate_compose_bootstrap(config)
        gen.assert_called_once_with(config, secrets=secrets, judge_password="TEMP")


def test_regenerate_compose_pulls_password_from_secrets(service, secrets, config):
    secrets.get_required.return_value = "real-judge-pw"
    with patch("dom.core.services.infra.service.generate_docker_compose") as gen:
        service.regenerate_compose(config)
        secrets.get_required.assert_called_once_with("judge_password")
        gen.assert_called_once_with(config, secrets=secrets, judge_password="real-judge-pw")


# ---------------------------------------------------------------- Lifecycle


def test_start_service_invokes_docker_with_compose_file(service, temp_dir):
    service.start_service("mariadb")
    service._docker_mock.start_services.assert_called_once_with(
        ["mariadb"], temp_dir / "docker-compose.yml"
    )


def test_wait_domserver_healthy_uses_container_prefix(service):
    with patch("dom.core.services.infra.service.get_container_prefix", return_value="dom-test"):
        service.wait_domserver_healthy()
    service._docker_mock.wait_for_container_healthy.assert_called_once()
    arg = service._docker_mock.wait_for_container_healthy.call_args.args[0]
    assert "dom-test" in arg


def test_fetch_and_store_judge_password_persists_to_secrets(service, secrets):
    service._docker_mock.fetch_judgedaemon_password.return_value = "fetched-pw"
    result = service.fetch_and_store_judge_password()
    assert result == "fetched-pw"
    secrets.set.assert_called_once_with("judge_password", "fetched-pw")


def test_start_judgehosts_generates_indexed_service_names(service, temp_dir):
    service.start_judgehosts(3)
    service._docker_mock.start_services.assert_called_once_with(
        ["judgehost-1", "judgehost-2", "judgehost-3"], temp_dir / "docker-compose.yml"
    )


def test_configure_admin_password_uses_config_password_when_provided(service, secrets, config):
    secrets.get_required.return_value = "db-pw"
    service.configure_admin_password(config)
    service._docker_mock.update_admin_password.assert_called_once_with(
        new_password="admin-pass", db_user="domjudge", db_password="db-pw"
    )
    secrets.set.assert_called_once_with("admin_password", "admin-pass")


def test_configure_admin_password_falls_back_to_stored_secret(service, secrets):
    config = InfraConfig(port=8080, judges=1, password=None)
    secrets.get.return_value = "stored-admin"
    secrets.get_required.return_value = "db-pw"
    service.configure_admin_password(config)
    service._docker_mock.update_admin_password.assert_called_once_with(
        new_password="stored-admin", db_user="domjudge", db_password="db-pw"
    )
    service._docker_mock.fetch_admin_init_password.assert_not_called()


def test_configure_admin_password_fetches_from_container_as_last_resort(service, secrets):
    config = InfraConfig(port=8080, judges=1, password=None)
    secrets.get.return_value = None
    secrets.get_required.return_value = "db-pw"
    service._docker_mock.fetch_admin_init_password.return_value = "container-init-pw"
    service.configure_admin_password(config)
    service._docker_mock.update_admin_password.assert_called_once_with(
        new_password="container-init-pw", db_user="domjudge", db_password="db-pw"
    )


# ---------------------------------------------------------------- Destruction


def test_destroy_without_volumes_preserves_secrets(service, secrets, temp_dir):
    service.destroy(remove_volumes=False)
    service._docker_mock.stop_all_services.assert_called_once_with(
        compose_file=temp_dir / "docker-compose.yml", remove_volumes=False
    )
    secrets.clear_all.assert_not_called()


def test_destroy_with_volumes_clears_secrets(service, secrets, temp_dir):
    service.destroy(remove_volumes=True)
    service._docker_mock.stop_all_services.assert_called_once_with(
        compose_file=temp_dir / "docker-compose.yml", remove_volumes=True
    )
    secrets.clear_all.assert_called_once()


# ---------------------------------------------------------------- Status


def test_check_status_returns_early_when_docker_unavailable(secrets):
    from dom.exceptions import DockerError

    with patch("dom.core.services.infra.service.DockerClient") as docker_cls:
        docker_cls.side_effect = DockerError("no docker")
        # Construct service after first DockerClient call has succeeded for __init__
        # We need DockerClient to succeed during __init__, then fail during check_status.
        # Easier: stub __init__ Docker, then re-patch for check_status.
    # Direct approach: patch with two calls, first OK, second raising.
    init_docker = MagicMock()
    init_docker._cmd = ["docker"]

    with (
        patch("dom.core.services.infra.service.DockerClient") as docker_cls,
        patch("dom.core.services.infra.service.ensure_dom_directory", return_value=Path("/tmp")),
    ):
        docker_cls.side_effect = [init_docker, DockerError("daemon down")]
        svc = InfraService(secrets)
        status = svc.check_status()

    assert status.docker_available is False
    assert status.docker_error == "daemon down"
    assert status.services == {}


def test_check_status_returns_empty_when_no_compose_file(service):
    # service fixture's temp_dir has no docker-compose.yml inside
    status = service.check_status()
    assert status.docker_available is True
    assert status.services == {}


def test_check_status_classifies_running_healthy_container(service, temp_dir):
    compose = temp_dir / "docker-compose.yml"
    compose.write_text("services:\n  domserver:\n    container_name: dom-domserver\n")

    def fake_run(cmd, **_):
        # First inspect: container state. Second: health.
        if "{{.State.Status}}" in cmd[2]:
            return MagicMock(returncode=0, stdout="running\n")
        return MagicMock(returncode=0, stdout="healthy\n")

    with patch("dom.core.services.infra.service.subprocess.run", side_effect=fake_run):
        status = service.check_status()

    assert status.services == {"domserver": ServiceStatus.HEALTHY}


def test_check_status_classifies_missing_container(service, temp_dir):
    compose = temp_dir / "docker-compose.yml"
    compose.write_text("services:\n  domserver:\n    container_name: dom-domserver\n")

    with patch("dom.core.services.infra.service.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        status = service.check_status()

    assert status.services == {"domserver": ServiceStatus.MISSING}


def test_check_status_classifies_stopped_container(service, temp_dir):
    compose = temp_dir / "docker-compose.yml"
    compose.write_text("services:\n  domserver:\n    container_name: dom-domserver\n")

    with patch("dom.core.services.infra.service.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="exited\n")
        status = service.check_status()

    assert status.services == {"domserver": ServiceStatus.STOPPED}


def test_check_status_classifies_starting_and_unhealthy(service, temp_dir):
    compose = temp_dir / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  domserver:\n    container_name: dom-domserver\n"
        "  judgehost-1:\n    container_name: dom-judgehost-1\n"
    )

    health_by_container = {"dom-domserver": "starting", "dom-judgehost-1": "unhealthy"}

    def fake_run(cmd, **_):
        container = cmd[-1]
        if "{{.State.Status}}" in cmd[2]:
            return MagicMock(returncode=0, stdout="running\n")
        return MagicMock(returncode=0, stdout=health_by_container[container] + "\n")

    with patch("dom.core.services.infra.service.subprocess.run", side_effect=fake_run):
        status = service.check_status()

    assert status.services["domserver"] == ServiceStatus.STARTING
    assert status.services["judgehost-1"] == ServiceStatus.UNHEALTHY
