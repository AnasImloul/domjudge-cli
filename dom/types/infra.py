from pydantic import BaseModel, SecretStr
from typing import Optional


class InfraConfig(BaseModel):
    port: int = 12345
    judges: int = 1
    password: Optional[SecretStr] = None

    def inspect(self):
        return {
            "port": self.port,
            "judges": self.judges,
            "password": self.password.get_secret_value()
        }

    class Config:
        frozen = True