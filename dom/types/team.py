from pydantic import BaseModel, SecretStr


class Team(BaseModel):
    name: str
    password: SecretStr

    class Config:
        frozen = True
