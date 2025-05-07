from typing import Optional
from pydantic import BaseModel, SecretStr, root_validator


class Team(BaseModel):
    id: Optional[str] = None
    name: str
    password: SecretStr

    def inspect(self):
        return {
            "name": self.name,
            "password": self.password.get_secret_value()
        }
