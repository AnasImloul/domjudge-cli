"""Tests for infrastructure validation with idempotency support."""

import socket
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dom.exceptions import ConfigError, DockerError, InfrastructureError
from dom.utils.prerequisites import (
    is_port_used_by_domjudge,
    validate_config_file,
    validate_docker_available,
    validate_infrastructure_prerequisites,
    validate_port_available,
    warn_if_privileged_port,
)


def test_validate_port_available_when_free():
    """Test that validation passes when port is free."""
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        free_port = s.getsockname()[1]

    # Should not raise
    validate_port_available(free_port)


def test_validate_port_available_when_used_by_other():
    """Test that validation fails when port is used by another process."""
    # Bind to a port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        used_port = s.getsockname()[1]

        # Should raise InfrastructureError
        with pytest.raises(InfrastructureError, match="already in use"):
            validate_port_available(used_port, allow_domjudge=False)


def test_validate_port_available_when_used_by_domjudge():
    """Test that validation passes when port is used by DOMjudge (idempotent)."""
    # Bind to a port to simulate it being in use
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        used_port = s.getsockname()[1]

        # Mock is_port_used_by_domjudge to return True
        with patch("dom.utils.prerequisites.is_port_used_by_domjudge", return_value=True):
            # Should NOT raise because it's our own infrastructure
            validate_port_available(used_port, allow_domjudge=True)


def test_is_port_used_by_domjudge_when_container_running():
    """Test detection of port usage by DOMjudge container."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "0.0.0.0:8080->80/tcp"

    with patch("subprocess.run", return_value=mock_result):
        assert is_port_used_by_domjudge(8080) is True


def test_is_port_used_by_domjudge_when_container_not_running():
    """Test detection when DOMjudge container is not running."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        assert is_port_used_by_domjudge(8080) is False


def test_is_port_used_by_domjudge_when_docker_fails():
    """Test graceful handling when docker command fails."""
    with patch("subprocess.run", side_effect=Exception("Docker not available")):
        # Should return False and not crash
        assert is_port_used_by_domjudge(8080) is False


def test_validate_port_available_with_allow_domjudge_false():
    """Test that allow_domjudge=False prevents idempotent behavior."""
    # Bind to a port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        used_port = s.getsockname()[1]

        # Even if DOMjudge is using it, should raise when allow_domjudge=False
        with patch("dom.utils.prerequisites.is_port_used_by_domjudge", return_value=True):
            with pytest.raises(InfrastructureError, match="already in use"):
                validate_port_available(used_port, allow_domjudge=False)


class TestValidateDockerAvailable:
    """Tests for validate_docker_available."""

    def test_passes_when_docker_returns_zero(self):
        result = MagicMock(returncode=0, stderr=b"")
        with patch("subprocess.run", return_value=result):
            validate_docker_available()  # should not raise

    def test_raises_with_permission_hint_on_permission_denied(self):
        result = MagicMock(returncode=1, stderr=b"permission denied while connecting to docker")
        with patch("subprocess.run", return_value=result):
            with pytest.raises(DockerError, match="permission denied"):
                validate_docker_available()

    def test_raises_with_daemon_hint_on_cannot_connect(self):
        result = MagicMock(returncode=1, stderr=b"Cannot connect to the Docker daemon")
        with patch("subprocess.run", return_value=result):
            with pytest.raises(DockerError, match="Cannot connect to Docker daemon"):
                validate_docker_available()

    def test_raises_generic_error_on_other_failure(self):
        result = MagicMock(returncode=1, stderr=b"something else went wrong")
        with patch("subprocess.run", return_value=result):
            with pytest.raises(DockerError, match="not functioning correctly"):
                validate_docker_available()

    def test_raises_install_hint_when_docker_missing(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(DockerError, match="not installed"):
                validate_docker_available()

    def test_raises_timeout_error_when_command_hangs(self):
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=5)
        ):
            with pytest.raises(DockerError, match="timed out"):
                validate_docker_available()


class TestValidateConfigFile:
    """Tests for validate_config_file."""

    def test_returns_provided_path_when_valid(self, temp_dir):
        cfg = temp_dir / "dom-judge.yaml"
        cfg.write_text("infra: {}")
        assert validate_config_file(cfg) == cfg

    def test_picks_up_default_yaml_when_path_is_none(self, temp_dir, monkeypatch):
        monkeypatch.chdir(temp_dir)
        (temp_dir / "dom-judge.yaml").write_text("infra: {}")
        assert validate_config_file(None) == Path("dom-judge.yaml")

    def test_picks_up_default_yml_when_only_yml_exists(self, temp_dir, monkeypatch):
        monkeypatch.chdir(temp_dir)
        (temp_dir / "dom-judge.yml").write_text("infra: {}")
        assert validate_config_file(None) == Path("dom-judge.yml")

    def test_raises_when_both_default_files_exist(self, temp_dir, monkeypatch):
        monkeypatch.chdir(temp_dir)
        (temp_dir / "dom-judge.yaml").write_text("")
        (temp_dir / "dom-judge.yml").write_text("")
        with pytest.raises(ConfigError, match="Both"):
            validate_config_file(None)

    def test_raises_when_no_default_file_exists(self, temp_dir, monkeypatch):
        monkeypatch.chdir(temp_dir)
        with pytest.raises(ConfigError, match="No configuration file found"):
            validate_config_file(None)

    def test_raises_when_provided_path_missing(self, temp_dir):
        with pytest.raises(ConfigError, match="not found"):
            validate_config_file(temp_dir / "missing.yaml")

    def test_raises_when_provided_path_is_directory(self, temp_dir):
        sub = temp_dir / "subdir"
        sub.mkdir()
        with pytest.raises(ConfigError, match="not a file"):
            validate_config_file(sub)

    def test_raises_when_file_is_unreadable(self, temp_dir):
        cfg = temp_dir / "dom-judge.yaml"
        cfg.write_text("infra: {}")
        with patch("pathlib.Path.open", side_effect=PermissionError):
            with pytest.raises(ConfigError, match="Permission denied"):
                validate_config_file(cfg)


class TestValidateInfrastructurePrerequisites:
    """Tests for the orchestrating validator."""

    def test_passes_when_docker_and_port_ok(self):
        with (
            patch("dom.utils.prerequisites.validate_docker_available"),
            patch("dom.utils.prerequisites.validate_port_available"),
        ):
            validate_infrastructure_prerequisites(port=8080)  # should not raise

    def test_propagates_docker_error(self):
        with patch(
            "dom.utils.prerequisites.validate_docker_available",
            side_effect=DockerError("nope"),
        ):
            with pytest.raises(DockerError):
                validate_infrastructure_prerequisites(port=8080)

    def test_propagates_port_error(self):
        with (
            patch("dom.utils.prerequisites.validate_docker_available"),
            patch(
                "dom.utils.prerequisites.validate_port_available",
                side_effect=InfrastructureError("busy"),
            ),
        ):
            with pytest.raises(InfrastructureError):
                validate_infrastructure_prerequisites(port=8080)

    def test_skips_port_check_when_port_is_none(self):
        with (
            patch("dom.utils.prerequisites.validate_docker_available"),
            patch("dom.utils.prerequisites.validate_port_available") as mock_port,
        ):
            validate_infrastructure_prerequisites(port=None)

        mock_port.assert_not_called()


class TestWarnIfPrivilegedPort:
    """Tests for warn_if_privileged_port."""

    def test_warns_for_privileged_port(self):
        with patch("dom.utils.prerequisites.console") as mock_console:
            warn_if_privileged_port(80)
        assert mock_console.print.called

    def test_silent_for_unprivileged_port(self):
        with patch("dom.utils.prerequisites.console") as mock_console:
            warn_if_privileged_port(8080)
        mock_console.print.assert_not_called()
