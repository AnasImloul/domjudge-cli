from pathlib import Path

from pydantic import BaseModel

from dom.types.contest import ContestConfig
from dom.types.infra import InfraConfig
from dom.utils.pydantic import InspectMixin


class DomConfig(InspectMixin, BaseModel):
    infra: InfraConfig = InfraConfig()
    contests: list[ContestConfig] = []
    loaded_from: Path

    class Config:
        frozen = True
