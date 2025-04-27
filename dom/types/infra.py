from pydantic import BaseModel, SecretStr
from typing import Optional


class InfraConfig(BaseModel):
    port: int = 12345
    judges: int = 1
    password: Optional[SecretStr] = None

    class Config:
        frozen = True