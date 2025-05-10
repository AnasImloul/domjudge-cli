from pydantic import BaseModel, Field, SecretStr
from typing import List, Union, Optional
from datetime import datetime


class RawInfraConfig(BaseModel):
    port: int = 12345
    judges: int = 1
    password: SecretStr = None

    class Config:
        frozen = True


class RawProblemsConfig(BaseModel):
    from_: str = Field(alias="from")

    class Config:
        frozen = True
        populate_by_name = True


class RawProblem(BaseModel):
    archive: str
    platform: str
    color: str

    class Config:
        frozen = True


class RawTeamsConfig(BaseModel):
    from_: str = Field(alias="from")
    delimiter: str = None
    rows: str
    name: str
    affiliation: str

    class Config:
        frozen = True
        populate_by_name = True


class RawContestConfig(BaseModel):
    name: str
    shortname: str = None
    formal_name: str = None
    start_time: datetime = None
    duration: str = None
    penalty_time: int = 0
    allow_submit: bool = True
    with_statement: bool = False

    problems: Union[RawProblemsConfig, List[RawProblem]]
    teams: RawTeamsConfig

    class Config:
        frozen = True


class RawDomConfig(BaseModel):
    infra: RawInfraConfig = RawInfraConfig()
    contests: Optional[List[RawContestConfig]] = []
    loaded_from: str

    class Config:
        frozen = True