"""Tests for CLI utility functions."""

from pathlib import Path

import pytest

from dom.utils.cli import find_file_with_extensions


class TestFindFileWithExtensions:
    """Tests for find_file_with_extensions function."""

    def test_finds_yaml_file(self, tmp_path: Path) -> None:
        """Test finding a .yaml file."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("test: value")

        result = find_file_with_extensions(
            base_path=tmp_path, base_name="test", extensions=(".yaml", ".yml")
        )

        assert result == test_file

    def test_finds_yml_file(self, tmp_path: Path) -> None:
        """Test finding a .yml file."""
        test_file = tmp_path / "test.yml"
        test_file.write_text("test: value")

        result = find_file_with_extensions(
            base_path=tmp_path, base_name="test", extensions=(".yaml", ".yml")
        )

        assert result == test_file

    def test_prefers_yaml_over_yml(self, tmp_path: Path) -> None:
        """Test that .yaml is checked before .yml."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("yaml: value")

        result = find_file_with_extensions(
            base_path=tmp_path, base_name="test", extensions=(".yaml", ".yml")
        )

        assert result == yaml_file

    def test_raises_when_both_extensions_exist(self, tmp_path: Path) -> None:
        """Test that FileExistsError is raised when both .yaml and .yml exist."""
        yaml_file = tmp_path / "test.yaml"
        yml_file = tmp_path / "test.yml"
        yaml_file.write_text("yaml: value")
        yml_file.write_text("yml: value")

        with pytest.raises(FileExistsError, match=r"Both 'test\.yaml' and 'test\.yml' exist"):
            find_file_with_extensions(
                base_path=tmp_path, base_name="test", extensions=(".yaml", ".yml")
            )

    def test_raises_when_no_file_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised when no file is found."""
        with pytest.raises(FileNotFoundError, match=r"No 'test\.yaml' or 'test\.yml' found"):
            find_file_with_extensions(
                base_path=tmp_path, base_name="test", extensions=(".yaml", ".yml")
            )

    def test_returns_explicit_file_path(self, tmp_path: Path) -> None:
        """Test that an explicit file path is returned as-is."""
        test_file = tmp_path / "explicit.yaml"
        test_file.write_text("test: value")

        result = find_file_with_extensions(
            base_path=test_file, base_name="ignored", extensions=(".yaml", ".yml")
        )

        assert result == test_file

    def test_searches_in_directory(self, tmp_path: Path) -> None:
        """Test searching for a file within a specific directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.yaml"
        test_file.write_text("test: value")

        result = find_file_with_extensions(
            base_path=subdir, base_name="test", extensions=(".yaml", ".yml")
        )

        assert result == test_file

    def test_error_context_included_in_exception(self, tmp_path: Path) -> None:
        """Test that error context is included in the exception message."""
        with pytest.raises(FileNotFoundError, match="Custom context"):
            find_file_with_extensions(
                base_path=tmp_path,
                base_name="test",
                extensions=(".yaml", ".yml"),
                error_context="Custom context",
            )

    def test_works_with_string_base_path(self, tmp_path: Path) -> None:
        """Test that the function works with string paths."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("test: value")

        result = find_file_with_extensions(
            base_path=str(tmp_path), base_name="test", extensions=(".yaml", ".yml")
        )

        assert result == test_file
