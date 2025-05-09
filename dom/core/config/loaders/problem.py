import tempfile
import zipfile
from pathlib import Path
from p2d import convert
from typing import Union, List
import yaml
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from dom.types.problem import ProblemPackage, ProblemData, ProblemINI, ProblemYAML, OutputValidators, Submissions
from dom.types.config.raw import RawProblemsConfig, RawProblem
from dom.utils.color import get_hex_color
from dom.utils.sys import load_folder_as_dict
from dom.utils.cli import ensure_dom_directory


def convert_and_load_problem(archive_path: Path) -> ProblemPackage:
    assert archive_path.exists(), f"Archive not found: {archive_path}"

    # Prepare a local cache for converted archives
    base_dom_dir = Path(ensure_dom_directory())
    cache_dir = base_dom_dir / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)

    cached_zip = cache_dir / f"{archive_path.stem}.zip"
    # If the cache is stale or missing, reconvert
    if not cached_zip.exists() or archive_path.stat().st_mtime > cached_zip.stat().st_mtime:
        convert(
            str(archive_path),
            str(cached_zip),
            short_name="-".join(archive_path.stem.split("-")[:-1])
        )

    # Work in a temporary directory for extraction
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        extract_dir = tmpdir / 'extracted'
        extract_dir.mkdir()

        # Extract the (cached) converted ZIP
        with zipfile.ZipFile(cached_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Load domjudge-problem.ini
        ini_path = extract_dir / 'domjudge-problem.ini'
        if not ini_path.exists():
            raise FileNotFoundError("Missing domjudge-problem.ini")
        ini_content = ini_path.read_text(encoding='utf-8')
        problem_ini = ProblemINI.parse(ini_content)

        # Load problem.yaml
        yaml_path = extract_dir / 'problem.yaml'
        if not yaml_path.exists():
            raise FileNotFoundError("Missing problem.yaml")
        yaml_content = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
        problem_yaml = ProblemYAML(**yaml_content)

        # Load data
        data = ProblemData(
            sample=load_folder_as_dict(extract_dir / 'data' / 'sample'),
            secret=load_folder_as_dict(extract_dir / 'data' / 'secret')
        )

        # Load output validators
        output_validators = OutputValidators(
            checker=load_folder_as_dict(extract_dir / 'output_validators' / 'checker')
        )

        # Load submissions
        submissions_dir = extract_dir / 'submissions'
        submissions_data = {}
        if submissions_dir.exists():
            for verdict_dir in submissions_dir.iterdir():
                if verdict_dir.is_dir():
                    submissions_data[verdict_dir.name] = load_folder_as_dict(verdict_dir)
        submissions = Submissions(**submissions_data)

        # Load additional root files
        files = {}
        for file_path in extract_dir.glob('*'):
            if file_path.is_file() and file_path.name not in {'domjudge-problem.ini', 'problem.yaml'}:
                files[file_path.name] = file_path.read_bytes()

        # Package up
        problem = ProblemPackage(
            ini=problem_ini,
            yaml=problem_yaml,
            data=data,
            output_validators=output_validators,
            submissions=submissions,
            files=files
        )

        # Validation: write to a temporary ZIP in its own temp directory to avoid Windows locks
        extracted_files = {str(p.relative_to(extract_dir)) for p in extract_dir.rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as tmp_zip_dir:
            tmp_zip_path = Path(tmp_zip_dir) / 'package.zip'
            written_files = problem.write_to_zip(tmp_zip_path)

        problem.validate_package(extracted_files, written_files)
        return problem


def load_domjudge_problem(archive_path: Path) -> ProblemPackage:
    """
    Load a DOMjudge problem archive and return a ProblemPackage.
    """
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        extract_dir = tmpdir / 'extracted'
        extract_dir.mkdir()

        # Extract the ZIP
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Load domjudge-problem.ini
        ini_path = extract_dir / 'domjudge-problem.ini'
        if not ini_path.exists():
            raise FileNotFoundError("Missing domjudge-problem.ini")
        ini_content = ini_path.read_text(encoding='utf-8')
        problem_ini = ProblemINI.parse(ini_content)

        # Load problem.yaml
        yaml_path = extract_dir / 'problem.yaml'
        if not yaml_path.exists():
            raise FileNotFoundError("Missing problem.yaml")
        yaml_content = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
        problem_yaml = ProblemYAML(**yaml_content)

        # Load sample/secret data
        data = ProblemData(
            sample=load_folder_as_dict(extract_dir / 'data' / 'sample'),
            secret=load_folder_as_dict(extract_dir / 'data' / 'secret')
        )

        # Load output validators
        output_validators = OutputValidators(
            checker=load_folder_as_dict(extract_dir / 'output_validators' / 'checker')
        )

        # Load submissions
        submissions_dir = extract_dir / 'submissions'
        submissions_data = {}
        if submissions_dir.exists():
            for verdict_dir in submissions_dir.iterdir():
                if verdict_dir.is_dir():
                    submissions_data[verdict_dir.name] = load_folder_as_dict(verdict_dir)

        submissions = Submissions(**submissions_data)

        # Load additional files
        files = {}
        for file_path in extract_dir.glob('*'):
            if file_path.is_file() and file_path.name not in {'domjudge-problem.ini', 'problem.yaml'}:
                files[file_path.name] = file_path.read_bytes()

        # Build and return ProblemPackage
        return ProblemPackage(
            ini=problem_ini,
            yaml=problem_yaml,
            data=data,
            output_validators=output_validators,
            submissions=submissions,
            files=files
        )


def load_problem(problem: RawProblem) -> ProblemPackage:
    """
    Import a problem based on its format.
    - 'domjudge': load directly
    - 'polygon': convert and load
    - Else: raise exception
    """
    problem_format = (problem.platform or "").strip().lower()

    if problem_format == "domjudge":
        problem_package = load_domjudge_problem(Path(problem.archive))
    elif problem_format == "polygon":
        problem_package = convert_and_load_problem(Path(problem.archive))
    else:
        raise ValueError(f"Unsupported problem platform: '{problem.platform}' (must be 'domjudge' or 'polygon')")

    problem_package.ini.color = get_hex_color(problem.color)
    return problem_package


def load_problems_from_config(problem_config: Union[RawProblemsConfig, List[RawProblem]], config_path: str):
    if isinstance(problem_config, RawProblemsConfig):
        file_path = problem_config.from_

        # Resolve file_path relative to the directory of config_path
        config_dir = os.path.dirname(os.path.abspath(config_path))
        file_path = os.path.join(config_dir, file_path)

        if not (file_path.endswith(".yml") or file_path.endswith(".yaml")):
            print(f"[ERROR] Problems file '{file_path}' must be a .yml or .yaml file.", file=sys.stderr)
            raise ValueError(f"Invalid file extension for problems file: {file_path}")

        if not os.path.exists(file_path):
            print(f"[ERROR] Problems file '{file_path}' does not exist.", file=sys.stderr)
            raise FileNotFoundError(f"Problems file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                loaded_data = yaml.safe_load(f)
                if not isinstance(loaded_data, list):
                    print(f"[ERROR] Problems file '{file_path}' must contain a list.", file=sys.stderr)
                    raise ValueError(f"Problems file must contain a list of problems: {file_path}")
                problems = [RawProblem(**problem) for problem in loaded_data]
        except Exception as e:
            print(f"[ERROR] Failed to load problems from '{file_path}'. Error: {str(e)}", file=sys.stderr)
            raise e

    elif isinstance(problem_config, list) and all(isinstance(p, RawProblem) for p in problem_config):
        problems = problem_config
    else:
        print(f"[ERROR] Invalid problem configuration.", file=sys.stderr)
        raise TypeError("Invalid problem configuration type.")

    # Validate archives are unique
    archive_paths = [os.path.abspath(problem.archive) for problem in problems]
    if len(archive_paths) != len(set(archive_paths)):
        duplicates = set([x for x in archive_paths if archive_paths.count(x) > 1])
        raise ValueError(f"Duplicate archives detected: {', '.join(duplicates)}")

    for idx, problem in enumerate(problems, start=1):
        if not os.path.exists(problem.archive):
            raise FileNotFoundError(f"Archive not found: {problem.archive}")

    # Load problems with progress bar
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(load_problem, problem): problem for problem in problems}
        problem_packages = []
        for future in tqdm(as_completed(futures), total=len(futures), desc="Loading problems"):
            problem_packages.append(future.result())

    # Validate short_names are unique
    short_names = [problem_package.ini.short_name for problem_package in problem_packages]
    if len(short_names) != len(set(short_names)):
        duplicates = set([x for x in short_names if short_names.count(x) > 1])
        raise ValueError(f"Duplicate problem short_names detected: {', '.join(duplicates)}")

    return problem_packages
