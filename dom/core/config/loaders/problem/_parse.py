"""Shared parsing for an extracted problem directory.

Both the DOMjudge-format and Polygon-format loaders end up with an
extracted directory laid out in the standard DOMjudge package shape
(``domjudge-problem.ini``, ``problem.yaml``, ``data/{sample,secret}/``,
``output_validators/checker/``, ``submissions/<verdict>/``). Parsing
that layout into a ``ProblemPackage`` lives here so the two format
loaders only own their format-specific pre-steps.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from dom.types.problem import (
    OutputValidators,
    ProblemData,
    ProblemINI,
    ProblemPackage,
    ProblemYAML,
    Submissions,
)
from dom.utils.sys import load_folder_as_dict


def parse_extracted_problem_dir(
    extract_dir: Path,
    *,
    collect_extra_files: bool = False,
) -> ProblemPackage:
    """Parse a standard DOMjudge problem layout from an extracted directory.

    When ``collect_extra_files`` is true, any file under ``extract_dir``
    that isn't part of the recognized layout is preserved on the
    package as raw bytes — used by the Polygon path so converter
    artefacts survive the round-trip.
    """
    ini_path = extract_dir / "domjudge-problem.ini"
    if not ini_path.exists():
        raise FileNotFoundError("Missing domjudge-problem.ini")
    problem_ini = ProblemINI.parse(ini_path.read_text(encoding="utf-8"))

    yaml_path = extract_dir / "problem.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError("Missing problem.yaml")
    problem_yaml = ProblemYAML(**yaml.safe_load(yaml_path.read_text(encoding="utf-8")))

    data = ProblemData(
        sample=load_folder_as_dict(extract_dir / "data" / "sample"),
        secret=load_folder_as_dict(extract_dir / "data" / "secret"),
    )

    output_validators = OutputValidators(
        checker=load_folder_as_dict(extract_dir / "output_validators" / "checker")
    )

    submissions_dir = extract_dir / "submissions"
    submissions_data: dict[str, dict[str, bytes]] = {}
    if submissions_dir.exists():
        for verdict_dir in submissions_dir.iterdir():
            if verdict_dir.is_dir():
                submissions_data[verdict_dir.name] = load_folder_as_dict(verdict_dir)
    submissions = Submissions(**submissions_data)

    extra_files: dict[str, bytes] = {}
    if collect_extra_files:
        tracked = {
            "domjudge-problem.ini",
            "problem.yaml",
            *[f"data/sample/{fn}" for fn in data.sample],
            *[f"data/secret/{fn}" for fn in data.secret],
            *[f"output_validators/checker/{fn}" for fn in output_validators.checker],
            *[
                f"submissions/{v}/{fn}"
                for v, fmap in submissions._verdicts().items()
                for fn in fmap
            ],
        }
        for p in extract_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(extract_dir).as_posix()
                if rel not in tracked:
                    extra_files[rel] = p.read_bytes()

    return ProblemPackage(
        ini=problem_ini,
        yaml=problem_yaml,
        data=data,
        output_validators=output_validators,
        submissions=submissions,
        extra_files=extra_files,
    )
