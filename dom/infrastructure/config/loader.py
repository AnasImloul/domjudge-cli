from pathlib import Path

import yaml

from dom.types.config.raw import RawDomConfig
from dom.utils.cli import find_config_or_default


def load_config(file_path: Path | None = None) -> RawDomConfig:
    config_path = find_config_or_default(file_path)
    with config_path.open() as f:
        return RawDomConfig(**yaml.safe_load(f), loaded_from=config_path)
