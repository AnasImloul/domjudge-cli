"""Integration tests for CLI commands."""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample configuration file."""
    config_content = """
infra:
  port: 12345
  judges: 2

contests:
  - name: "Test Contest"
    shortname: "TEST2025"
    start_time: "2025-06-01T10:00:00+00:00"
    duration: "5:00:00.000"
    penalty_time: 20
    allow_submit: true
    with_statement: false

    problems:
      - archive: "problem1.zip"
        platform: "Polygon"
        color: "blue"

    teams:
      from: "teams.csv"
      delimiter: ","
      rows: "2-10"
      name: "$2"
      affiliation: "$3"
"""
    config_file = tmp_path / "test-config.yaml"
    config_file.write_text(config_content)

    # Also create a dummy teams file
    teams_file = tmp_path / "teams.csv"
    teams_file.write_text("id,name,affiliation\n1,Team A,School A\n")

    return config_file


class TestInitCommand:
    """Tests for 'dom init' command."""

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_init_command_help(self, cli_runner):
        """Test that init command shows help."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output


class TestInfraCommands:
    """Tests for 'dom infra' commands."""

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_infra_help(self, cli_runner):
        """Test that infra command shows help."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["infra", "--help"])
        assert result.exit_code == 0
        assert "infrastructure" in result.output.lower()

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_infra_status_help(self, cli_runner):
        """Test that infra status shows help."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["infra", "status", "--help"])
        assert result.exit_code == 0


class TestContestCommands:
    """Tests for 'dom contest' commands."""

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_contest_help(self, cli_runner):
        """Test that contest command shows help."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["contest", "--help"])
        assert result.exit_code == 0
        assert "contest" in result.output.lower()

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_contest_apply_help(self, cli_runner):
        """Test that contest apply shows help."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["contest", "apply", "--help"])
        assert result.exit_code == 0
        assert "Apply" in result.output
        assert "--dry-run" in result.output

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_contest_apply_missing_config(self, cli_runner, tmp_path):
        """Test that contest apply fails gracefully without config."""
        from dom.cli import app

        with patch("os.getcwd", return_value=str(tmp_path)):
            with patch("os.path.isfile", return_value=False):
                result = cli_runner.invoke(app, ["contest", "apply"])
                assert result.exit_code == 1

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_contest_inspect_help(self, cli_runner):
        """Test that contest inspect shows help."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["contest", "inspect", "--help"])
        assert result.exit_code == 0
        assert "Inspect" in result.output
        assert "--show-secrets" in result.output


class TestErrorHandling:
    """Tests for error handling in CLI."""

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_invalid_command(self, cli_runner):
        """Test that invalid command shows error."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    def test_missing_required_argument(self, cli_runner):
        """Test that missing required argument shows error."""
        from dom.cli import app

        result = cli_runner.invoke(app, ["contest", "verify-problemset"])
        assert result.exit_code != 0


class TestDryRunIntegration:
    """Integration tests for dry-run functionality."""

    @pytest.mark.skip(reason="Requires full app initialization with templates")
    @patch("dom.cli.contest.get_secrets_manager")
    @patch("dom.core.config.loaders.load_config")
    @patch("dom.cli.contest._preview_contest_changes")
    def test_contest_apply_dry_run(
        self, mock_preview, mock_load_config, mock_secrets, cli_runner, sample_config_file
    ):
        """Test contest apply with --dry-run flag."""
        from dom.cli import app

        # Mock dependencies
        mock_secrets.return_value = Mock()
        mock_config = Mock()
        mock_load_config.return_value = mock_config

        result = cli_runner.invoke(
            app, ["contest", "apply", "--file", str(sample_config_file), "--dry-run"]
        )

        # Should succeed
        assert result.exit_code == 0

        # Should call preview, not apply
        mock_preview.assert_called_once()
        mock_load_config.assert_called_once()
