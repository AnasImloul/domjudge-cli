import yaml
from dom.types.config.raw import RawDomConfig
from dom.utils.cli import find_config_or_default


def load_config(file_path: str = None) -> RawDomConfig:
    file_path = find_config_or_default(file_path)
    with open(file_path, "r") as f:
        return RawDomConfig(
            **yaml.safe_load(f),
            loaded_from=file_path
        )
