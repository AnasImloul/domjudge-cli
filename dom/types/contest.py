from datetime import datetime

from pydantic import BaseModel

from dom.types.problem import ProblemPackage
from dom.types.team import Team
from dom.utils.pydantic import InspectMixin


class ContestConfig(InspectMixin, BaseModel):
    name: str
    shortname: str | None = None
    formal_name: str | None = None
    start_time: datetime | None = None
    duration: str | None = None
    penalty_time: int | None = 0
    allow_submit: bool | None = True
    with_statement: bool | None = False

    problems: list[ProblemPackage]
    teams: list[Team]
