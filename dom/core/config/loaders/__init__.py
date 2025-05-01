from typing import List
from dom.types.config.processed import DomConfig, InfraConfig, ContestConfig
from dom.infrastructure.config import load_config as load_raw_config
from .contest import load_contests_from_config, load_contest_from_config
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


def load_contest_config(file_path: str | None, contest_name: str) -> ContestConfig:
    config = load_raw_config(file_path)

    if not config.contests:
        raise ValueError(
            f"No contests found in the provided config file"
            f"{f' ({config.loaded_from})' if config.loaded_from else ''}."
        )

    for contest in config.contests:
        if contest.shortname == contest_name:
            return load_contest_from_config(contest, config_path=config.loaded_from)

    available_contests = [contest.shortname for contest in config.contests]
    raise KeyError(
        f"Contest with name '{contest_name}' wasn't found in the config file"
        f"{f' ({config.loaded_from})' if config.loaded_from else ''}. "
        f"Available contests: {', '.join(map(lambda contest:f"'{contest}'", available_contests))}"
    )
