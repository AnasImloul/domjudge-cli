"""Integration tests for the dom CLI.

These tests invoke the Typer app via ``CliRunner`` to verify command
wiring, help text, and validation paths end-to-end. They don't reach
DOMjudge or Docker — those concerns are covered by service-level unit
tests with mocked clients.
"""

from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from dom.cli import app

# Rich/Click can interleave ANSI color escapes inside flag names when
# terminal width is narrow (CI), breaking simple substring matches like
# ``"--dry-run" in result.output``. Strip them before asserting on text.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _plain(output: str) -> str:
    return _ANSI.sub("", output)


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------- top-level


def test_root_shows_help_when_no_subcommand(cli_runner):
    result = cli_runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Manage DOMjudge" in _plain(result.output)


def test_version_flag_exits_zero(cli_runner):
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "dom-cli version" in _plain(result.output)


def test_invalid_command_exits_nonzero(cli_runner):
    result = cli_runner.invoke(app, ["invalid-command"])
    assert result.exit_code != 0


# ---------------------------------------------------------------- init


class TestInit:
    def test_init_help(self, cli_runner):
        result = cli_runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "init" in _plain(result.output).lower()


# ---------------------------------------------------------------- infra


class TestInfra:
    def test_infra_help(self, cli_runner):
        result = cli_runner.invoke(app, ["infra", "--help"])
        assert result.exit_code == 0
        assert "infrastructure" in _plain(result.output).lower()

    def test_infra_status_help(self, cli_runner):
        result = cli_runner.invoke(app, ["infra", "status", "--help"])
        assert result.exit_code == 0

    def test_infra_apply_help_lists_dry_run(self, cli_runner):
        result = cli_runner.invoke(app, ["infra", "apply", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in _plain(result.output)


# ---------------------------------------------------------------- contest


class TestContest:
    def test_contest_help(self, cli_runner):
        result = cli_runner.invoke(app, ["contest", "--help"])
        assert result.exit_code == 0
        assert "contest" in _plain(result.output).lower()

    def test_contest_apply_help_lists_dry_run(self, cli_runner):
        result = cli_runner.invoke(app, ["contest", "apply", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in _plain(result.output)

    def test_contest_inspect_help(self, cli_runner):
        result = cli_runner.invoke(app, ["contest", "inspect", "--help"])
        assert result.exit_code == 0

    def test_contest_verify_problemset_requires_args(self, cli_runner):
        # Missing the required <contest> argument should fail the
        # parser, not silently exit zero.
        result = cli_runner.invoke(app, ["contest", "verify-problemset"])
        assert result.exit_code != 0


# ---------------------------------------------------------------- error paths


class TestErrors:
    def test_contest_apply_missing_config_exits_nonzero(self, cli_runner, tmp_path, monkeypatch):
        # Run from an empty dir so the loader can't find dom-judge.yaml.
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(app, ["contest", "apply"])
        assert result.exit_code != 0
