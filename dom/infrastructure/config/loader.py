import yaml

def load_config(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return yaml.safe_load(f)
