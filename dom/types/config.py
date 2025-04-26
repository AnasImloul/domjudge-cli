from pydantic import BaseModel, Field
from typing import List, Union
from datetime import datetime


class InfraConfig(BaseModel):
    port: int = 12345
    judges: int = 1
    password: str = None

    class Config:
        frozen = True


class ProblemsConfig(BaseModel):
    from_: str = Field(alias="from")

    class Config:
        frozen = True
        populate_by_name = True


class Problem(BaseModel):
    archive: str
    platform: str
    color: str

    class Config:
        frozen = True


class TeamsConfig(BaseModel):
    from_: str = Field(alias="from")
    delimiter: str = None
    rows: str
    name: str

    class Config:
        frozen = True
        populate_by_name = True


class ContestConfig(BaseModel):
    name: str
    shortname: str = None
    formal_name: str = None
    start_time: datetime = None
    duration: str = None
    penalty_time: int = 0
    allow_submit: bool = True

    problems: Union[ProblemsConfig, List[Problem]]
    teams: TeamsConfig

    class Config:
        frozen = True


class DomConfig(BaseModel):
    infra: InfraConfig = InfraConfig()
    contests: List[ContestConfig] = []

    class Config:
        frozen = True