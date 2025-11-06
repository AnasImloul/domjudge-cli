"""Tests for infrastructure state comparison using Docker as source of truth."""

import subprocess
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from dom.core.services.infra.state import (
    InfraChangeSet,
    InfraChangeType,
    InfraStateComparator,
)
from dom.types.infra import InfraConfig


class TestInfraStateComparator:
    """Tests for InfraStateComparator."""

    def test_compare_infrastructure_creates_new_when_no_containers(self):
        """Test that CREATE is returned when no containers exist."""
        comparator = InfraStateComparator()
        new_config = InfraConfig(port=8080, judges=4, password=SecretStr("test123"))

        with patch("subprocess.run") as mock_run:
            # Docker inspect returns non-zero (container doesn't exist)
            mock_run.return_value = MagicMock(returncode=1)

            result = comparator.compare_infrastructure(new_config)

            assert result.change_type == InfraChangeType.CREATE
            assert result.old_config is None
            assert result.new_config == new_config

    def test_compare_infrastructure_no_change_when_identical(self):
        """Test that NO_CHANGE is returned when configs are identical."""
        comparator = InfraStateComparator()
        config = InfraConfig(port=8080, judges=4, password=SecretStr("test123"))

        with patch.object(comparator, "_load_current_state", return_value=config):
            result = comparator.compare_infrastructure(config)

            assert result.change_type == InfraChangeType.NO_CHANGE
            assert result.old_config == config
            assert result.new_config == config

    def test_compare_infrastructure_scale_judges_up(self):
        """Test that SCALE_JUDGES is detected when increasing judge count."""
        comparator = InfraStateComparator()
        old_config = InfraConfig(port=8080, judges=4, password=SecretStr("test123"))
        new_config = InfraConfig(port=8080, judges=8, password=SecretStr("test123"))

        with patch.object(comparator, "_load_current_state", return_value=old_config):
            result = comparator.compare_infrastructure(new_config)

            assert result.change_type == InfraChangeType.SCALE_JUDGES
            assert result.judge_diff == 4
            assert result.is_safe_live_change is True
            assert result.requires_restart is False

    def test_compare_infrastructure_scale_judges_down(self):
        """Test that SCALE_JUDGES is detected when decreasing judge count."""
        comparator = InfraStateComparator()
        old_config = InfraConfig(port=8080, judges=8, password=SecretStr("test123"))
        new_config = InfraConfig(port=8080, judges=4, password=SecretStr("test123"))

        with patch.object(comparator, "_load_current_state", return_value=old_config):
            result = comparator.compare_infrastructure(new_config)

            assert result.change_type == InfraChangeType.SCALE_JUDGES
            assert result.judge_diff == -4
            assert result.is_safe_live_change is True

    def test_compare_infrastructure_port_change_requires_restart(self):
        """Test that port changes require restart."""
        comparator = InfraStateComparator()
        old_config = InfraConfig(port=8080, judges=4, password=SecretStr("test123"))
        new_config = InfraConfig(port=9090, judges=4, password=SecretStr("test123"))

        with patch.object(comparator, "_load_current_state", return_value=old_config):
            result = comparator.compare_infrastructure(new_config)

            assert result.change_type == InfraChangeType.PORT_CHANGE
            assert result.is_safe_live_change is False
            assert result.requires_restart is True

    def test_compare_infrastructure_password_change_requires_restart(self):
        """Test that password changes require restart."""
        comparator = InfraStateComparator()
        old_config = InfraConfig(port=8080, judges=4, password=SecretStr("old"))
        new_config = InfraConfig(port=8080, judges=4, password=SecretStr("new"))

        with patch.object(comparator, "_load_current_state", return_value=old_config):
            result = comparator.compare_infrastructure(new_config)

            assert result.change_type == InfraChangeType.PASSWORD_CHANGE
            assert result.requires_restart is True

    def test_compare_infrastructure_multiple_changes_full_restart(self):
        """Test that multiple changes trigger full restart."""
        comparator = InfraStateComparator()
        old_config = InfraConfig(port=8080, judges=4, password=SecretStr("old"))
        new_config = InfraConfig(port=9090, judges=8, password=SecretStr("new"))

        with patch.object(comparator, "_load_current_state", return_value=old_config):
            result = comparator.compare_infrastructure(new_config)

            assert result.change_type == InfraChangeType.FULL_RESTART
            assert result.requires_restart is True

    def test_get_container_port_extracts_port_correctly(self):
        """Test that port is correctly extracted from docker port command."""
        comparator = InfraStateComparator()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="0.0.0.0:8080\n")

            port = comparator._get_container_port("test-container")

            assert port == 8080
            mock_run.assert_called_once()

    def test_get_container_port_returns_none_when_container_not_found(self):
        """Test that None is returned when container doesn't exist."""
        comparator = InfraStateComparator()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            port = comparator._get_container_port("nonexistent")

            assert port is None

    def test_count_judgehost_containers_counts_correctly(self):
        """Test that judgehost containers are counted correctly."""
        comparator = InfraStateComparator()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="judgehost-1\njudgehost-2\njudgehost-3\n"
            )

            count = comparator._count_judgehost_containers()

            assert count == 3

    def test_count_judgehost_containers_returns_zero_on_error(self):
        """Test that 0 is returned when docker command fails."""
        comparator = InfraStateComparator()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "docker")

            count = comparator._count_judgehost_containers()

            assert count == 0

    def test_load_current_state_returns_none_when_no_domserver(self):
        """Test that None is returned when domserver doesn't exist."""
        comparator = InfraStateComparator()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            state = comparator._load_current_state()

            assert state is None

    def test_change_set_summary_for_create(self):
        """Test summary message for CREATE change."""
        change_set = InfraChangeSet(
            change_type=InfraChangeType.CREATE,
            old_config=None,
            new_config=InfraConfig(port=8080, judges=4, password=SecretStr("test")),
        )

        summary = change_set.summary()

        assert "CREATE" in summary
        assert "new infrastructure" in summary

    def test_change_set_summary_for_scale_up(self):
        """Test summary message for scaling up judges."""
        old = InfraConfig(port=8080, judges=4, password=SecretStr("test"))
        new = InfraConfig(port=8080, judges=8, password=SecretStr("test"))

        change_set = InfraChangeSet(
            change_type=InfraChangeType.SCALE_JUDGES, old_config=old, new_config=new, judge_diff=4
        )

        summary = change_set.summary()

        assert "SCALE UP" in summary
        assert "4" in summary
        assert "8" in summary
        assert "safe live change" in summary
