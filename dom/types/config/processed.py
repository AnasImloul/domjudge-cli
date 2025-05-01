from pydantic import BaseModel
from typing import List
from dom.types.contest import ContestConfig
from dom.types.infra import InfraConfig


class DomConfig(BaseModel):
    infra: InfraConfig = InfraConfig()
    contests: List[ContestConfig] = []
    loaded_from: str

    class Config:
        frozen = True