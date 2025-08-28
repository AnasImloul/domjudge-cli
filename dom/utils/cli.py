import os
from typing import Optional
from rich.prompt import Confirm
from dom.cli import console


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

    yaml_exists = os.path.isfile("dom-judge.yaml")
    yml_exists = os.path.isfile("dom-judge.yml")

    if yaml_exists and yml_exists:
        raise FileExistsError("Both 'dom-judge.yaml' and 'dom-judge.yml' exist. Please specify which one to use.")
    if not yaml_exists and not yml_exists:
        raise FileNotFoundError("No 'dom-judge.yaml' or 'dom-judge.yml' found. Please specify a config file.")

    return "dom-judge.yaml" if yaml_exists else "dom-judge.yml"

def check_file_exists(file: str) -> bool:
    if os.path.isfile(file):
        raise FileExistsError(f"File '{file}' already exists. Rename or remove the existing file, or use --overwrite to replace it.")
    return False


def ask_override_if_exists(output_file: str) -> bool:
    """Ask user whether to override if the output file exists."""

    if os.path.exists(output_file):
        override = Confirm.ask(
            f"File '{output_file}' exists. Do you want to override it?",
            default=False, console=console
        )
        if not override:
            console.print("[yellow]Skipping problem initialization.[/yellow]")
            return False
    return True