from pathlib import Path

import yaml

from dom.types.config.raw import RawDomConfig
from dom.utils.cli import find_config_or_default


def load_config(file_path: str | None = None) -> RawDomConfig:
    file_path = find_config_or_default(file_path)
    with Path(file_path).open() as f:
        return RawDomConfig(**yaml.safe_load(f), loaded_from=file_path)
