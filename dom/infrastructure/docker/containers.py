import subprocess
from typing import List
import os

def start_services(services: List[str], compose_file: str) -> None:
    print(os.system("ls"))
    cmd = ["sudo", "docker", "compose", "-f", compose_file, "up", "-d"] + services
    subprocess.run(cmd, check=True)

def stop_all_services(compose_file: str) -> None:
    cmd = ["sudo", "docker", "compose", "-f", compose_file, "down", "-v"]
    subprocess.run(cmd, check=True)


import subprocess
import re


def fetch_judgedaemon_password() -> str:
    cmd = ["sudo", "docker", "exec", "dom-cli-domserver", "cat", "/opt/domjudge/domserver/etc/restapi.secret"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    # Define regex pattern:
    # Match: any_word whitespace any_url whitespace any_word whitespace password
    pattern = re.compile(r"^\S+\s+\S+\s+\S+\s+(\S+)$", re.MULTILINE)

    match = pattern.search(result.stdout.strip())
    if not match:
        raise ValueError("Failed to parse judgedaemon password from output")

    password = match.group(1)
    return password
