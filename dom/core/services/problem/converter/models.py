import zipfile
from pathlib import Path
from typing import Dict, Set

import yaml
from pydantic import BaseModel


class ProblemINI(BaseModel):
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


class ProblemYAML(BaseModel):
    limits: Dict[str, int]
    name: str
    validation: str

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        content = yaml.safe_dump(self.dict(), sort_keys=False)
        path = "problem.yaml"
        zf.writestr(path, content)
        return {path}


class ProblemData(BaseModel):
    sample: Dict[str, bytes]
    secret: Dict[str, bytes]

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        written = set()
        for group, files in [("sample", self.sample), ("secret", self.secret)]:
            for filename, content in files.items():
                path = f"data/{group}/{filename}"
                zf.writestr(path, content)
                written.add(path)
        return written


class OutputValidators(BaseModel):
    checker: Dict[str, bytes]

    def write_to_zip(self, zf: zipfile.ZipFile) -> Set[str]:
        written = set()
        for filename, content in self.checker.items():
            path = f"output_validators/checker/{filename}"
            zf.writestr(path, content)
            written.add(path)
        return written


class Submissions(BaseModel):
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
            for filename, content in files.items():
                path = f"submissions/{verdict}/{filename}"
                zf.writestr(path, content)
                written.add(path)
        return written


class ProblemPackage(BaseModel):
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
            raise ValueError(f"[ERROR] Missing expected files: {sorted(missing)}")
        if unexpected:
            for path in sorted(unexpected):
                print(f"[WARNING] Unexpected file found: {path}")
