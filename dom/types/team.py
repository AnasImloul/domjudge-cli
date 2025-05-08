from typing import Optional
from pydantic import BaseModel, SecretStr, root_validator
from dom.utils.pydantic import InspectMixin

class Team(InspectMixin, BaseModel):
    id: Optional[str] = None
    name: str
    password: SecretStr
