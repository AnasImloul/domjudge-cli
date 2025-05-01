from typing import List
from dom.types.config.processed import DomConfig, InfraConfig, ContestConfig
from dom.infrastructure.config import load_config as load_raw_config
from .contest import load_contests_from_config
from .infra import load_infra_from_config



def load_config(file_path: str | None) -> DomConfig:
    config = load_raw_config(file_path)
    return DomConfig(
        infra=load_infra_from_config(config.infra, config_path=config.loaded_from),
        contests=load_contests_from_config(config.contests, config_path=config.loaded_from),
        loaded_from=config.loaded_from
    )


def load_infrastructure_config(file_path: str | None) -> InfraConfig:
    config = load_raw_config(file_path)
    return load_infra_from_config(config.infra, config_path=config.loaded_from)


def load_contests_config(file_path: str | None) -> List[ContestConfig]:
    config = load_raw_config(file_path)
    return load_contests_from_config(config.contests, config_path=config.loaded_from)
