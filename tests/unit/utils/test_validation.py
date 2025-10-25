"""Tests for infrastructure validation with idempotency support."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from dom.exceptions import InfrastructureError
from dom.utils.validation import is_port_used_by_domjudge, validate_port_available


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
        with patch("dom.utils.validation.is_port_used_by_domjudge", return_value=True):
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
        with patch("dom.utils.validation.is_port_used_by_domjudge", return_value=True):
            with pytest.raises(InfrastructureError, match="already in use"):
                validate_port_available(used_port, allow_domjudge=False)
