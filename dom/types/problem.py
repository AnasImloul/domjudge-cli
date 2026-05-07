import zipfile
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from dom.logging_config import get_logger
from dom.utils.pydantic import InspectMixin

logger = get_logger(__name__)


def write_files_to_zip(zf: zipfile.ZipFile, base_path: str, files: dict[str, bytes]) -> set[str]:
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
        data: dict[str, Any] = {}
        for line in content.strip().splitlines():
            if "=" not in line:
                continue
            key, value = (part.strip() for part in line.split("=", 1))
            data[key.replace("-", "_")] = float(value) if key == "timelimit" else value
        return cls(**data)

    def write_to_zip(self, zf: zipfile.ZipFile) -> set[str]:
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
    limits: dict[str, int]
    name: str
    validation: str

    def write_to_zip(self, zf: zipfile.ZipFile) -> set[str]:
        content = yaml.safe_dump(self.model_dump(), sort_keys=False)
        path = "problem.yaml"
        zf.writestr(path, content)
        return {path}


class ProblemData(InspectMixin, BaseModel):
    sample: dict[str, bytes]
    secret: dict[str, bytes]

    def write_to_zip(self, zf: zipfile.ZipFile) -> set[str]:
        written = set()
        written.update(write_files_to_zip(zf, "data/sample", self.sample))
        written.update(write_files_to_zip(zf, "data/secret", self.secret))
        return written


class OutputValidators(InspectMixin, BaseModel):
    checker: dict[str, bytes]

    def write_to_zip(self, zf: zipfile.ZipFile) -> set[str]:
        return write_files_to_zip(zf, "output_validators/checker", self.checker)


class Submissions(InspectMixin, BaseModel):
    accepted: dict[str, bytes] = {}
    time_limit_exceeded: dict[str, bytes] = {}
    wrong_answer: dict[str, bytes] = {}
    memory_limit_exceeded: dict[str, bytes] = {}
    runtime_error: dict[str, bytes] = {}
    mixed: dict[str, bytes] = {}

    def _verdicts(self) -> dict[str, dict[str, bytes]]:
        return {field: getattr(self, field) for field in type(self).model_fields}

    def write_to_zip(self, zf: zipfile.ZipFile) -> set[str]:
        written = set()
        for verdict, files in self._verdicts().items():
            written.update(write_files_to_zip(zf, f"submissions/{verdict}", files))
        return written


class ProblemPackage(InspectMixin, BaseModel):
    id: str | None = None
    ini: ProblemINI
    yaml: ProblemYAML
    data: ProblemData
    output_validators: OutputValidators
    submissions: Submissions
    extra_files: dict[str, bytes] = {}

    def write_to_zip(self, output_path: Path) -> set[str]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        written_paths = set()
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            written_paths.update(self.ini.write_to_zip(zf))
            written_paths.update(self.yaml.write_to_zip(zf))
            written_paths.update(self.data.write_to_zip(zf))
            written_paths.update(self.output_validators.write_to_zip(zf))
            written_paths.update(self.submissions.write_to_zip(zf))
            # write back any extra untracked files
            for rel_path, content in self.extra_files.items():
                zf.writestr(rel_path, content)
                written_paths.add(rel_path)
        return written_paths

    def validate_package(self, extracted_files: set[str], written_files: set[str]) -> None:
        missing = written_files - extracted_files
        unexpected = extracted_files - written_files
        if missing:
            logger.error("Missing expected files: %s", sorted(missing))
        for path in sorted(unexpected):
            logger.warning("Unexpected file found: %s", path)
