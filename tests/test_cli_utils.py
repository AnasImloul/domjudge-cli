"""Tests for CLI utility functions."""

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from dom.exceptions import DomJudgeCliError
from dom.utils.cli import (
    check_file_exists,
    cli_command,
    ensure_dom_directory,
    find_config_or_default,
    get_secrets_manager,
)


class TestEnsureDomDirectory:
    """Tests for ensure_dom_directory function."""

    def test_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test that .dom directory is created if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        dom_path = ensure_dom_directory()
        assert dom_path.exists()
        assert dom_path == tmp_path / ".dom"

    def test_returns_existing_directory(self, tmp_path, monkeypatch):
        """Test that existing .dom directory is returned."""
        dom_dir = tmp_path / ".dom"
        dom_dir.mkdir()

        monkeypatch.chdir(tmp_path)
        dom_path = ensure_dom_directory()
        assert dom_path == dom_dir


class TestGetSecretsManager:
    """Tests for get_secrets_manager function."""

    def test_returns_secrets_manager(self, tmp_path, monkeypatch):
        """Test that secrets manager is created."""
        monkeypatch.chdir(tmp_path)
        manager = get_secrets_manager()
        assert manager is not None
        assert manager.secrets_dir == Path(tmp_path / ".dom")


class TestCliCommand:
    """Tests for cli_command decorator."""

    def test_successful_execution(self):
        """Test that successful command executes normally."""

        @cli_command
        def test_func(x: int) -> int:
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_catches_domjudge_cli_error(self):
        """Test that DomJudgeCliError is caught and exits with code 1."""

        @cli_command
        def test_func():
            raise DomJudgeCliError("Test error")

        with pytest.raises(typer.Exit) as exc_info:
            test_func()

        assert exc_info.value.exit_code == 1

    def test_catches_keyboard_interrupt(self):
        """Test that KeyboardInterrupt exits with code 130."""

        @cli_command
        def test_func():
            raise KeyboardInterrupt()

        with pytest.raises(typer.Exit) as exc_info:
            test_func()

        assert exc_info.value.exit_code == 130

    def test_catches_unexpected_exception(self):
        """Test that unexpected exceptions are caught and exit with code 1."""

        @cli_command
        def test_func():
            raise RuntimeError("Unexpected error")

        with pytest.raises(typer.Exit) as exc_info:
            test_func()

        assert exc_info.value.exit_code == 1


class TestFindConfigOrDefault:
    """Tests for find_config_or_default function."""

    def test_returns_specified_file_if_exists(self, tmp_path):
        """Test that specified file is returned if it exists."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text("test: config")

        result = find_config_or_default(config_file)
        assert result == config_file

    def test_raises_error_if_specified_file_not_exists(self):
        """Test that FileNotFoundError is raised if specified file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="not found"):
            find_config_or_default(Path("nonexistent.yaml"))

    def test_finds_yaml_file_by_default(self, tmp_path, monkeypatch):
        """Test that dom-judge.yaml is found by default."""
        # Create the file in tmp_path
        yaml_file = tmp_path / "dom-judge.yaml"
        yaml_file.write_text("test: config")

        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        result = find_config_or_default(None)
        assert result == Path("dom-judge.yaml")

    def test_finds_yml_file_by_default(self, tmp_path, monkeypatch):
        """Test that dom-judge.yml is found if .yaml doesn't exist."""
        # Create only the .yml file
        yml_file = tmp_path / "dom-judge.yml"
        yml_file.write_text("test: config")

        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        result = find_config_or_default(None)
        assert result == Path("dom-judge.yml")

    def test_raises_error_if_both_yaml_and_yml_exist(self):
        """Test that error is raised if both .yaml and .yml exist."""
        with (
            patch("pathlib.Path.is_file", return_value=True),
            pytest.raises(FileExistsError, match="Both"),
        ):
            find_config_or_default(None)

    def test_raises_error_if_no_config_found(self):
        """Test that error is raised if no config file found."""
        with (
            patch("pathlib.Path.is_file", return_value=False),
            pytest.raises(FileNotFoundError, match="No 'dom-judge"),
        ):
            find_config_or_default(None)


class TestCheckFileExists:
    """Tests for check_file_exists function."""

    def test_raises_error_if_file_exists(self, tmp_path):
        """Test that FileExistsError is raised if file exists."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("exists")

        with pytest.raises(FileExistsError, match="already exists"):
            check_file_exists(existing_file)

    def test_returns_false_if_file_not_exists(self, tmp_path):
        """Test that False is returned if file doesn't exist."""
        nonexistent_file = tmp_path / "nonexistent.txt"

        result = check_file_exists(nonexistent_file)
        assert result is False
