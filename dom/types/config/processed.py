from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dom.types.contest import ContestConfig
from dom.types.infra import InfraConfig
from dom.utils.pydantic import InspectMixin


class DomConfig(InspectMixin, BaseModel):
    model_config = ConfigDict(frozen=True)

    infra: InfraConfig = InfraConfig()
    contests: list[ContestConfig] = []
    loaded_from: Path
