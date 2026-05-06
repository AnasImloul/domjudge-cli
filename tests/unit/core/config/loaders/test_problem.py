"""Tests for the problem config loader.

These tests focus on the orchestration paths in `load_problems_from_config`
(file resolution, error handling, duplicate detection) and the `load_problem`
dispatcher. Building real Polygon/DOMjudge archives requires the `p2d`
toolchain and is exercised by integration/e2e tests.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dom.core.config.loaders.problem import (
    load_problem,
    load_problems_from_config,
)
from dom.types.config.raw import RawProblem, RawProblemsConfig


def _write_archive(path: Path) -> None:
    path.write_bytes(b"placeholder")


def _make_inline(archives: list[Path], platform: str = "domjudge") -> list[RawProblem]:
    return [
        RawProblem(archive=str(p), platform=platform, color="red", with_statement=True)
        for p in archives
    ]


# ---------------------------------------------------------------------------
# load_problem dispatch
# ---------------------------------------------------------------------------


def test_load_problem_rejects_unknown_platform(tmp_path):
    archive = tmp_path / "p.zip"
    _write_archive(archive)
    with pytest.raises(ValueError, match="Unsupported problem platform"):
        load_problem(archive, platform="unknown", color="red", with_statement=True, idx=0)


def test_load_problem_dispatches_to_domjudge_loader(tmp_path):
    archive = tmp_path / "p.zip"
    _write_archive(archive)
    package = MagicMock()
    package.ini = MagicMock()

    with patch(
        "dom.core.config.loaders.problem.load_domjudge_problem", return_value=package
    ) as loader:
        result, idx = load_problem(archive, "domjudge", color="red", with_statement=True, idx=7)

    loader.assert_called_once_with(archive)
    assert result is package
    assert idx == 7


def test_load_problem_dispatches_to_polygon_loader(tmp_path):
    archive = tmp_path / "p.zip"
    _write_archive(archive)
    package = MagicMock()
    package.ini = MagicMock()

    with patch(
        "dom.core.config.loaders.problem.convert_and_load_problem", return_value=package
    ) as loader:
        load_problem(archive, "polygon", color="blue", with_statement=False, idx=0)

    loader.assert_called_once_with(archive, with_statement=False)


# ---------------------------------------------------------------------------
# load_problems_from_config: error paths (run before any process pool work)
# ---------------------------------------------------------------------------


def test_rejects_unknown_config_type(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    with pytest.raises(TypeError, match="Invalid problem configuration type"):
        load_problems_from_config("not-a-config", config_path)  # type: ignore[arg-type]


def test_inline_missing_archive_raises(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    problems = _make_inline([tmp_path / "missing.zip"])
    with pytest.raises(FileNotFoundError, match="Archive not found"):
        load_problems_from_config(problems, config_path)


def test_inline_duplicate_archives_rejected(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    archive = tmp_path / "p.zip"
    _write_archive(archive)
    problems = _make_inline([archive, archive])
    with pytest.raises(ValueError, match="Duplicate archives"):
        load_problems_from_config(problems, config_path)


def test_explicit_yaml_path_must_exist(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    cfg = RawProblemsConfig(**{"from": "missing.yaml"})
    with pytest.raises(FileNotFoundError, match="Problems file not found"):
        load_problems_from_config(cfg, config_path)


def test_default_lookup_fails_when_no_problems_file(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    cfg = RawProblemsConfig()
    with pytest.raises(FileNotFoundError):
        load_problems_from_config(cfg, config_path)


def test_directory_from_lookup_fails_when_no_problems_file(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    subdir = tmp_path / "sub"
    subdir.mkdir()
    cfg = RawProblemsConfig(**{"from": "sub"})
    with pytest.raises(FileNotFoundError):
        load_problems_from_config(cfg, config_path)


def test_problems_yaml_must_be_a_list(tmp_path):
    config_path = tmp_path / "dom-judge.yaml"
    problems_yaml = tmp_path / "problems.yaml"
    problems_yaml.write_text("not_a_list: true\n")
    cfg = RawProblemsConfig(**{"from": "problems.yaml"})
    with pytest.raises(ValueError, match="must contain a list"):
        load_problems_from_config(cfg, config_path)


def test_default_lookup_resolves_problems_yaml_relative_to_config(tmp_path):
    """Default lookup finds problems.yaml next to the config file and surfaces
    its archive validation (not FileNotFoundError on the YAML itself)."""
    config_path = tmp_path / "dom-judge.yaml"
    problems_yaml = tmp_path / "problems.yaml"
    problems_yaml.write_text(
        "- archive: nope.zip\n  platform: domjudge\n  color: red\n  with_statement: true\n"
    )
    cfg = RawProblemsConfig()
    with pytest.raises(FileNotFoundError, match="Archive not found"):
        load_problems_from_config(cfg, config_path)
