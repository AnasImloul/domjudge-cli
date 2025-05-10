from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from dom.types.problem import ProblemPackage
from dom.types.team import Team
from dom.utils.pydantic import InspectMixin


class ContestConfig(InspectMixin, BaseModel):
    name: str
    shortname: Optional[str] = None
    formal_name: Optional[str] = None
    start_time: Optional[datetime] = None
    duration: Optional[str] = None
    penalty_time: Optional[int] = 0
    allow_submit: Optional[bool] = True
    with_statement: Optional[bool] = False

    problems: List[ProblemPackage]
    teams: List[Team]
