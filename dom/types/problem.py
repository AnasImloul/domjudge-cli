import zipfile
from pathlib import Path
from typing import Any, Dict, Set, Optional

import yaml
from pydantic import BaseModel
from dom.utils.pydantic import InspectMixin

def write_files_to_zip(zf: zipfile.ZipFile, base_path: str, files: Dict[str, bytes]) -> Set[str]:
    written = set()
    for filename, content in files.items():
        path = f"{base_path}/{filename}"
        zf.writestr(path, content)
        written.add(path)
    return written


class ProblemINI(InspectMixin, BaseModel):
    short_name: str
    timelimit: float
    color: str
    externalid: str

    @classmethod
    def parse(cls, content: str) -> "ProblemINI":
        data = {}
        for line in content.strip().splitlines():
            if '=' in line:
                key, value = map(str.strip, line.split('=', 1))
                if key == "timelimit":
                    value = float(value)
                data[key.replace('-', '_')] = value
        return cls(**data)

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        content = (
            f"short-name = {self.short_name}\n"
            f"timelimit = {self.timelimit}\n"
            f"color = {self.color}\n"
            f"externalid = {self.externalid}\n"
        )
        path = "domjudge-problem.ini"
        zf.writestr(path, content)
        return {path}


class ProblemYAML(InspectMixin, BaseModel):
    limits: Dict[str, int]
    name: str
    validation: str

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        content = yaml.safe_dump(self.dict(), sort_keys=False)
        path = "problem.yaml"
        zf.writestr(path, content)
        return {path}


class ProblemData(InspectMixin, BaseModel):
    sample: Dict[str, bytes]
    secret: Dict[str, bytes]

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        written = set()
        written.update(write_files_to_zip(zf, "data/sample", self.sample))
        written.update(write_files_to_zip(zf, "data/secret", self.secret))
        return written


class OutputValidators(InspectMixin, BaseModel):
    checker: Dict[str, bytes]

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        return write_files_to_zip(zf, "output_validators/checker", self.checker)


class Submissions(InspectMixin, BaseModel):
    accepted: Dict[str, bytes] = {}
    time_limit_exceeded: Dict[str, bytes] = {}
    wrong_answer: Dict[str, bytes] = {}
    memory_limit_exceeded: Dict[str, bytes] = {}
    runtime_error: Dict[str, bytes] = {}
    mixed: Dict[str, bytes] = {}

    def _verdicts(self) -> Dict[str, Dict[str, bytes]]:
        return {
            field: getattr(self, field)
            for field in self.model_fields.keys()
            if isinstance(getattr(self, field), dict)
        }

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        written = set()
        for verdict, files in self._verdicts().items():
            written.update(write_files_to_zip(zf, f"submissions/{verdict}", files))
        return written


class ProblemPackage(InspectMixin, BaseModel):
    id: Optional[str] = None
    ini: ProblemINI
    yaml: ProblemYAML
    data: ProblemData
    output_validators: OutputValidators
    submissions: Submissions

    def write_to_zip(self, output_path: Path) -> Set[str]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        written_paths = set()
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            written_paths.update(self.ini.write_to_zip(zf))
            written_paths.update(self.yaml.write_to_zip(zf))
            written_paths.update(self.data.write_to_zip(zf))
            written_paths.update(self.output_validators.write_to_zip(zf))
            written_paths.update(self.submissions.write_to_zip(zf))
        return written_paths

    def validate_package(self, extracted_files: Set[str], written_files: Set[str]) -> None:
        missing = written_files - extracted_files
        unexpected = extracted_files - written_files
        if missing:
            print(f"[ERROR] Missing expected files: {sorted(missing)}")
        if unexpected:
            for path in sorted(unexpected):
                print(f"[WARNING] Unexpected file found: {path}")
