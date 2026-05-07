import tempfile
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Union

import yaml
from p2d import convert

from dom.logging_config import get_logger
from dom.types.config.raw import RawProblem, RawProblemsConfig
from dom.types.problem import (
    OutputValidators,
    ProblemData,
    ProblemINI,
    ProblemPackage,
    ProblemYAML,
    Submissions,
)
from dom.utils.cli import find_file_with_extensions
from dom.utils.color import get_hex_color
from dom.utils.sys import load_folder_as_dict

logger = get_logger(__name__)


def convert_and_load_problem(archive_path: Path, with_statement: bool) -> ProblemPackage:
    """Convert a Polygon archive to a DOMjudge package and load it (no caching)."""
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    # Always convert into a fresh temporary ZIP
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        # Path for the converted ZIP
        converted_zip = tmpdir_path / f"{archive_path.stem}.zip"

        # Perform conversion
        convert(
            str(archive_path),
            str(converted_zip),
            short_name="-".join(archive_path.stem.split("-")[:-1]),
            with_statement=with_statement,
        )

        # Work in a subdirectory for extraction
        extract_dir = tmpdir_path / "extracted"
        extract_dir.mkdir()

        # Extract the converted ZIP
        with zipfile.ZipFile(converted_zip, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Load domjudge-problem.ini
        ini_path = extract_dir / "domjudge-problem.ini"
        if not ini_path.exists():
            raise FileNotFoundError("Missing domjudge-problem.ini")
        problem_ini = ProblemINI.parse(ini_path.read_text(encoding="utf-8"))

        # Load problem.yaml
        yaml_path = extract_dir / "problem.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError("Missing problem.yaml")
        problem_yaml = ProblemYAML(**yaml.safe_load(yaml_path.read_text(encoding="utf-8")))

        # Load data folders
        data = ProblemData(
            sample=load_folder_as_dict(extract_dir / "data" / "sample"),
            secret=load_folder_as_dict(extract_dir / "data" / "secret"),
        )

        # Load output validators
        output_validators = OutputValidators(
            checker=load_folder_as_dict(extract_dir / "output_validators" / "checker")
        )

        # Load submissions
        submissions_dir = extract_dir / "submissions"
        submissions_data = {}
        if submissions_dir.exists():
            for verdict_dir in submissions_dir.iterdir():
                if verdict_dir.is_dir():
                    submissions_data[verdict_dir.name] = load_folder_as_dict(verdict_dir)
        submissions = Submissions(**submissions_data)

        # Collect extra files
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
        extra_files = {}
        for p in extract_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(extract_dir).as_posix()
                if rel not in tracked:
                    extra_files[rel] = p.read_bytes()

        # Build package
        problem = ProblemPackage(
            ini=problem_ini,
            yaml=problem_yaml,
            data=data,
            output_validators=output_validators,
            submissions=submissions,
            extra_files=extra_files,
        )

        # Validation write/read
        extracted_files = {
            str(p.relative_to(extract_dir)) for p in extract_dir.rglob("*") if p.is_file()
        }
        with tempfile.TemporaryDirectory() as tmp_zip_dir:
            tmp_zip_path = Path(tmp_zip_dir) / "package.zip"
            written_files = problem.write_to_zip(tmp_zip_path)

        problem.validate_package(extracted_files, written_files)
        return problem


def load_domjudge_problem(archive_path: Path) -> ProblemPackage:
    """
    Load a DOMjudge problem archive and return a ProblemPackage.
    """
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        extract_dir = tmpdir / "extracted"
        extract_dir.mkdir()

        # Extract the ZIP
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Load domjudge-problem.ini
        ini_path = extract_dir / "domjudge-problem.ini"
        if not ini_path.exists():
            raise FileNotFoundError("Missing domjudge-problem.ini")
        ini_content = ini_path.read_text(encoding="utf-8")
        problem_ini = ProblemINI.parse(ini_content)

        # Load problem.yaml
        yaml_path = extract_dir / "problem.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError("Missing problem.yaml")
        yaml_content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        problem_yaml = ProblemYAML(**yaml_content)

        # Load sample/secret data
        data = ProblemData(
            sample=load_folder_as_dict(extract_dir / "data" / "sample"),
            secret=load_folder_as_dict(extract_dir / "data" / "secret"),
        )

        # Load output validators
        output_validators = OutputValidators(
            checker=load_folder_as_dict(extract_dir / "output_validators" / "checker")
        )

        # Load submissions
        submissions_dir = extract_dir / "submissions"
        submissions_data = {}
        if submissions_dir.exists():
            for verdict_dir in submissions_dir.iterdir():
                if verdict_dir.is_dir():
                    submissions_data[verdict_dir.name] = load_folder_as_dict(verdict_dir)

        submissions = Submissions(**submissions_data)

        # Build and return ProblemPackage
        return ProblemPackage(
            ini=problem_ini,
            yaml=problem_yaml,
            data=data,
            output_validators=output_validators,
            submissions=submissions,
        )


def load_problem(
    archive_path: Path, platform: str, color: str, with_statement: bool, idx: int
) -> tuple[ProblemPackage, int]:
    """
    Import a problem based on its format.
    - 'domjudge': load directly
    - 'polygon': convert and load
    - Else: raise exception
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
):
    config_dir = config_path.resolve().parent

    if isinstance(problem_config, RawProblemsConfig):
        # Check if from_ is None (default lookup) or provided
        if problem_config.from_ is None:
            # Default: look for problems.yaml/problems.yml in the same directory as config
            try:
                file_path = find_file_with_extensions(
                    base_path=config_dir,
                    base_name="problems",
                    error_context="No 'from' path provided and no default problems file found.",
                )
            except FileNotFoundError as e:
                logger.error(str(e))
                raise
        else:
            # Resolve file_path relative to the directory of config_path
            from_path = config_dir / problem_config.from_

            # Check if from_path has a file extension
            if from_path.suffix.lower() in (".yml", ".yaml"):
                # Explicit file path provided
                file_path = from_path
                if not file_path.exists():
                    logger.error(f"Problems file '{file_path}' does not exist.")
                    raise FileNotFoundError(f"Problems file not found: {file_path}")
            else:
                # Directory path provided or base name without extension
                # Look for problems.yaml/problems.yml in that location
                try:
                    file_path = find_file_with_extensions(
                        base_path=from_path,
                        base_name="problems",
                        error_context=f"No problems.yaml or problems.yml found in '{from_path}'.",
                    )
                except FileNotFoundError as e:
                    logger.error(str(e))
                    raise
    elif isinstance(problem_config, list):
        problems = problem_config
        file_path = None
    else:
        logger.error("Invalid problem configuration.")
        raise TypeError("Invalid problem configuration type.")

    if file_path is not None:
        try:
            with file_path.open() as f:
                loaded_data = yaml.safe_load(f)
            if not isinstance(loaded_data, list):
                logger.error(f"Problems file '{file_path}' must contain a list.")
                raise ValueError(f"Problems file must contain a list of problems: {file_path}")
            problems = [RawProblem(**problem) for problem in loaded_data]
        except (OSError, yaml.YAMLError, ValueError, TypeError):
            logger.error(f"Failed to load problems from '{file_path}'", exc_info=True)
            raise

    archive_paths = [Path(problem.archive).resolve() for problem in problems]
    duplicates = [p for p, n in Counter(map(str, archive_paths)).items() if n > 1]
    if duplicates:
        raise ValueError(f"Duplicate archives detected: {', '.join(duplicates)}")

    for archive_path in archive_paths:
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

    # Load problems with progress bar
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

        # The parent operation already shows progress; no inner display needed.
        results = [future.result() for future in as_completed(futures)]
        problem_packages = [pkg for pkg, _ in sorted(results, key=lambda r: r[1])]

    short_names = [problem_package.ini.short_name for problem_package in problem_packages]
    duplicates = [name for name, n in Counter(short_names).items() if n > 1]
    if duplicates:
        raise ValueError(f"Duplicate problem short_names detected: {', '.join(duplicates)}")

    return problem_packages
