from typing import Optional
from pydantic import BaseModel, SecretStr
from dom.utils.pydantic import InspectMixin


class Team(InspectMixin, BaseModel):
    id: Optional[str] = None
    name: str
    affiliation: Optional[str] = None
    username: str = None
    password: SecretStr
