from pydantic import BaseModel, SecretStr
from typing import Optional
from dom.utils.pydantic import InspectMixin


class InfraConfig(InspectMixin, BaseModel):
    port: int = 12345
    judges: int = 1
    password: Optional[SecretStr] = None


    class Config:
        frozen = True