import yaml
from dom.types.config import DomConfig
from dom.utils.cli import find_config_or_default


def load_config(file_path: str = None) -> DomConfig:
    file_path = find_config_or_default(file_path)
    with open(file_path, "r") as f:
        return DomConfig(**yaml.safe_load(f))
