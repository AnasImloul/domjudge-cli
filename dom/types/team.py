from typing import Optional
from pydantic import BaseModel, SecretStr, root_validator


class Team(BaseModel):
    id: Optional[str] = None
    name: str
    password: SecretStr