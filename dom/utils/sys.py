from typing import Dict
from pathlib import Path

def load_folder_as_dict(base_path: Path) -> Dict[str, bytes]:
    if not base_path.exists():
        return {}
    return {file.name: file.read_bytes() for file in base_path.glob('*') if file.is_file()}
