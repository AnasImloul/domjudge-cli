import yaml

def load_config(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return yaml.safe_load(f)

def validate_config(filepath: str):
    config = load_config(filepath)
    # Dummy simple validation for MVP
    if "contests" not in config:
        raise ValueError("Missing 'contests' key in configuration.")
    # Extend validation logic later!
