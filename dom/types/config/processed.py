"""Processed configuration models.

This module contains the final processed configuration models after validation
and transformation from raw YAML config.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, SecretStr

from dom.types.problem import ProblemPackage
from dom.types.team import Team
from dom.utils.pydantic import InspectMixin


class InfraConfig(InspectMixin, BaseModel):
    """Infrastructure configuration model."""

    port: int = 12345
    judges: int = 1
    password: SecretStr | None = None

    class Config:
        frozen = True


class ContestConfig(InspectMixin, BaseModel):
    """Contest configuration model."""

    name: str
    shortname: str | None = None
    formal_name: str | None = None
    start_time: datetime | None = None
    duration: str | None = None
    penalty_time: int | None = 0
    allow_submit: bool | None = True

    problems: list[ProblemPackage]
    teams: list[Team]


class DomConfig(InspectMixin, BaseModel):
    """Top-level configuration model for the entire application."""

    infra: InfraConfig = InfraConfig()
    contests: list[ContestConfig] = []
    loaded_from: Path

    class Config:
        frozen = True
