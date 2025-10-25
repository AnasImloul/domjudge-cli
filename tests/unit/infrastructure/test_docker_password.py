"""Tests for bcrypt password handling in Docker operations."""

from unittest.mock import MagicMock, patch

import pytest

from dom.infrastructure.docker.containers import DockerClient


def test_bcrypt_password_escaping():
    """Test that bcrypt passwords with $ characters are properly escaped."""
    docker_client = DockerClient()

    # Typical bcrypt hash format: $2b$05$...
    bcrypt_hash = "$2b$05$wiOGpTKDcfYGeCDwRGuuvezRHWDasSWWLo2zVqeC6atUH.o3A2g.2"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # This should not raise
        docker_client._update_admin_password_via_docker(
            hashed_password=bcrypt_hash, db_user="domjudge", db_password="test_password"
        )

        # Verify subprocess.run was called
        assert mock_run.called

        # Get the command that was executed
        call_args = mock_run.call_args
        cmd = call_args[0][0]

        # Find the SQL query in the command
        sql_query = cmd[-1]  # Last argument is the --execute query

        # Verify the query structure is correct (direct UPDATE with escaped password)
        assert "UPDATE domjudge.user SET password = " in sql_query
        assert "WHERE username = 'admin'" in sql_query
        assert bcrypt_hash in sql_query, "Original bcrypt hash should be in the query"


def test_bcrypt_password_with_single_quotes():
    """Test handling of passwords with single quotes (edge case)."""
    docker_client = DockerClient()

    # Hypothetical password with single quote (shouldn't happen with bcrypt, but test anyway)
    password_with_quote = "$2b$05$test'value"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        docker_client._update_admin_password_via_docker(
            hashed_password=password_with_quote, db_user="domjudge", db_password="test_password"
        )

        # Get the SQL query
        cmd = mock_run.call_args[0][0]
        sql_query = cmd[-1]

        # Single quotes should be escaped with backslash
        assert "test\\'value" in sql_query, "Single quotes should be escaped with backslash"
        # Verify the query structure
        assert "UPDATE domjudge.user SET password = " in sql_query
        assert "WHERE username = 'admin'" in sql_query


def test_docker_exec_failure_handling():
    """Test that docker exec failures are properly handled."""
    docker_client = DockerClient()

    bcrypt_hash = "$2b$05$test"

    with patch("subprocess.run") as mock_run:
        # Simulate command failure
        mock_run.side_effect = __import__("subprocess").CalledProcessError(
            returncode=1, cmd=["docker", "exec"], stderr="ERROR: Connection failed"
        )

        # Should raise DockerError
        from dom.exceptions import DockerError

        with pytest.raises(DockerError, match="Failed to update admin password"):
            docker_client._update_admin_password_via_docker(
                hashed_password=bcrypt_hash, db_user="domjudge", db_password="test_password"
            )


def test_various_bcrypt_formats():
    """Test different bcrypt hash formats to ensure all are handled correctly."""
    docker_client = DockerClient()

    # Different bcrypt versions and costs
    test_hashes = [
        "$2a$10$abcdefghijklmnopqrstuv",  # 2a version
        "$2b$12$abcdefghijklmnopqrstuv",  # 2b version, higher cost
        "$2y$05$abcdefghijklmnopqrstuv",  # 2y version
    ]

    for bcrypt_hash in test_hashes:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            docker_client._update_admin_password_via_docker(
                hashed_password=bcrypt_hash, db_user="domjudge", db_password="test_password"
            )

            # Verify $ characters are properly escaped
            cmd = mock_run.call_args[0][0]
            sql_query = cmd[-1]

            # Verify the query structure is correct
            assert "UPDATE domjudge.user SET password = " in sql_query
            assert "WHERE username = 'admin'" in sql_query
            assert (
                bcrypt_hash in sql_query
            ), f"Original bcrypt hash should be in the query: {bcrypt_hash}"
