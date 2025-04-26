import os
from typing import Optional


def ensure_dom_directory() -> str:
    """
    Ensure that the .dom directory exists in the current working directory.
    Returns the absolute path to the .dom folder.
    """
    dom_path = os.path.join(os.getcwd(), ".dom")
    os.makedirs(dom_path, exist_ok=True)
    return dom_path


def find_config_or_default(file: Optional[str]) -> str:
    if file:
        if not os.path.isfile(file):
            raise FileNotFoundError(f"Specified config file '{file}' not found.")
        return file

    yaml_exists = os.path.isfile("dom-config.yaml")
    yml_exists = os.path.isfile("dom-config.yml")

    if yaml_exists and yml_exists:
        raise FileExistsError("Both 'dom-config.yaml' and 'dom-config.yml' exist. Please specify which one to use.")
    if not yaml_exists and not yml_exists:
        raise FileNotFoundError("No 'dom-config.yaml' or 'dom-config.yml' found. Please specify a config file.")

    return "dom-config.yaml" if yaml_exists else "dom-config.yml"
