"""Problem loaders.

Public API:
    - ``load_problem``: dispatch a single archive to the right format loader.
    - ``load_problems_from_config``: resolve a ``RawProblemsConfig`` (or
      inline list) and load every archive in parallel.

Format-specific loaders (``load_domjudge_problem``,
``convert_and_load_problem``) are re-exported here so callers — and
tests that patch at the package path — don't need to know which
submodule owns a given format.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Union

from dom.core.config.loaders.problem._resolve import resolve_problems_list
from dom.core.config.loaders.problem.domjudge import load_domjudge_problem
from dom.core.config.loaders.problem.polygon import convert_and_load_problem
from dom.types.config.raw import RawProblem, RawProblemsConfig
from dom.types.problem import ProblemPackage
from dom.utils.color import get_hex_color

__all__ = [
    "convert_and_load_problem",
    "load_domjudge_problem",
    "load_problem",
    "load_problems_from_config",
]


def load_problem(
    archive_path: Path, platform: str, color: str, with_statement: bool, idx: int
) -> tuple[ProblemPackage, int]:
    """Dispatch ``archive_path`` to the loader for ``platform``.

    Returns the loaded package alongside ``idx`` so callers can restore
    the original ordering after parallel execution.
    """
    problem_format = (platform or "").strip().lower()

    if problem_format == "domjudge":
        problem_package = load_domjudge_problem(archive_path)
    elif problem_format == "polygon":
        problem_package = convert_and_load_problem(archive_path, with_statement=with_statement)
    else:
        raise ValueError(
            f"Unsupported problem platform: '{platform}' (must be 'domjudge' or 'polygon')"
        )

    problem_package.ini.color = get_hex_color(color)
    return problem_package, idx


def load_problems_from_config(
    problem_config: Union[RawProblemsConfig, list[RawProblem]],
    config_path: Path,
) -> list[ProblemPackage]:
    """Resolve the problems list and load every archive in parallel."""
    problems = resolve_problems_list(problem_config, config_path)

    archive_paths = [Path(problem.archive).resolve() for problem in problems]
    duplicates = [p for p, n in Counter(map(str, archive_paths)).items() if n > 1]
    if duplicates:
        raise ValueError(f"Duplicate archives detected: {', '.join(duplicates)}")

    for archive_path in archive_paths:
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(
                load_problem,
                archive_path,
                problem.platform,
                problem.color,
                problem.with_statement,
                i,
            ): problem
            for i, (problem, archive_path) in enumerate(zip(problems, archive_paths, strict=False))
        }
        results = [future.result() for future in as_completed(futures)]
        problem_packages = [pkg for pkg, _ in sorted(results, key=lambda r: r[1])]

    short_names = [pkg.ini.short_name for pkg in problem_packages]
    duplicates = [name for name, n in Counter(short_names).items() if n > 1]
    if duplicates:
        raise ValueError(f"Duplicate problem short_names detected: {', '.join(duplicates)}")

    return problem_packages
