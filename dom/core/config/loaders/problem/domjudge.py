"""Loader for archives already in DOMjudge package format."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from dom.core.config.loaders.problem._parse import parse_extracted_problem_dir
from dom.types.problem import ProblemPackage


def load_domjudge_problem(archive_path: Path) -> ProblemPackage:
    """Extract a DOMjudge problem ZIP and load it into a ``ProblemPackage``."""
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        extract_dir = Path(tmpdir_str) / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        return parse_extracted_problem_dir(extract_dir)
