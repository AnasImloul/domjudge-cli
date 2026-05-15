"""Loader for Polygon archives.

Polygon packages are converted to DOMjudge layout via ``p2d`` and then
parsed through the shared parser. Converter artefacts that aren't part
of the recognized layout are preserved as ``extra_files`` so the
resulting package round-trips cleanly through ``write_to_zip``.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from p2d import convert

from dom.core.config.loaders.problem._parse import parse_extracted_problem_dir
from dom.types.problem import ProblemPackage


def convert_and_load_problem(archive_path: Path, with_statement: bool) -> ProblemPackage:
    """Convert a Polygon archive to a DOMjudge package and load it."""
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        converted_zip = tmpdir / f"{archive_path.stem}.zip"

        convert(
            str(archive_path),
            str(converted_zip),
            short_name="-".join(archive_path.stem.split("-")[:-1]),
            with_statement=with_statement,
        )

        extract_dir = tmpdir / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(converted_zip, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        package = parse_extracted_problem_dir(extract_dir, collect_extra_files=True)

        # Validate the package round-trips cleanly: writing it back to a
        # zip should reproduce the same file set we just extracted.
        extracted_files = {
            str(p.relative_to(extract_dir)) for p in extract_dir.rglob("*") if p.is_file()
        }
        with tempfile.TemporaryDirectory() as tmp_zip_dir:
            tmp_zip_path = Path(tmp_zip_dir) / "package.zip"
            written_files = package.write_to_zip(tmp_zip_path)

        package.validate_package(extracted_files, written_files)
        return package
