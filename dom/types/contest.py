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

    problems: List[ProblemPackage]
    teams: List[Team]

    def inspect(self):
        return {
            "name": self.name,
            "shortname": self.shortname,
            "formal_name": self.formal_name,
            "start_time": self.start_time,
            "duration": self.duration,
            "penalty_time": self.penalty_time,
            "allow_submit": self.allow_submit,
            "problems": [
                problem.inspect() for problem in self.problems
            ],
            "teams": [
                team.inspect() for team in self.teams
            ]
        }