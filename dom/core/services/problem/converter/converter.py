import tempfile
import zipfile
from pathlib import Path
from typing import Dict

import yaml
from p2d import convert
from .models import ProblemPackage, ProblemData, ProblemINI, ProblemYAML, OutputValidators, Submissions
from dom.utils.color import get_hex_color


def load_folder_as_dict(base_path: Path) -> Dict[str, bytes]:
    if not base_path.exists():
        return {}
    return {file.name: file.read_bytes() for file in base_path.glob('*') if file.is_file()}


def convert_and_load_problem(archive_path: Path) -> ProblemPackage:
    assert archive_path.exists()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        converted_zip = tmpdir / 'converted.zip'

        # Convert Polygon package to Domjudge package
        convert(
            str(archive_path),
            str(converted_zip),
            short_name="-".join(archive_path.stem.split("-")[:-1])
        )

        # Extract the converted ZIP
        extract_dir = tmpdir / 'extracted'
        extract_dir.mkdir()

        with zipfile.ZipFile(converted_zip, 'r') as zip_ref:
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

        # Load additional root files (not already known ones)
        files = {}
        for file_path in extract_dir.glob('*'):
            if file_path.is_file() and file_path.name not in {'domjudge-problem.ini', 'problem.yaml'}:
                files[file_path.name] = file_path.read_bytes()

        # Create the ProblemPackage model
        problem = ProblemPackage(
            ini=problem_ini,
            yaml=problem_yaml,
            data=data,
            output_validators=output_validators,
            submissions=submissions,
            files=files
        )

        # Perform validation
        extracted_files = {str(p.relative_to(extract_dir)) for p in extract_dir.rglob('*') if p.is_file()}

        # To get the written files, we simulate writing into a dummy zipfile
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp_zip_file:
            written_files = problem.write_to_zip(Path(tmp_zip_file.name))

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


from dom.types.config import Problem  # Assuming where your Problem model is

def import_problem(problem: Problem) -> ProblemPackage:
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
        raise ValueError(f"Unsupported problem format: '{problem.format}' (must be 'domjudge' or 'polygon')")

    problem_package.ini.color = get_hex_color(problem.color)
    return problem_package
