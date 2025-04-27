from typing import List
import os
import time
import re
import subprocess
from dom.utils.hash import generate_bcrypt_password



def start_services(services: List[str], compose_file: str) -> None:
    cmd = ["sudo", "docker", "compose", "-f", compose_file, "up", "-d", "--remove-orphans"] + services
    subprocess.run(cmd, check=True)


def stop_all_services(compose_file: str) -> None:
    cmd = ["sudo", "docker", "compose", "-f", compose_file, "down", "-v"]
    subprocess.run(cmd, check=True)


def wait_for_container_healthy(container_name: str, timeout: int = 60) -> None:
    """Wait until the specified Docker container is healthy or until timeout."""
    start_time = time.time()

    while True:
        cmd = ["sudo", "docker", "inspect", "--format={{.State.Health.Status}}", container_name]
        result = subprocess.run(cmd, capture_output=True, text=True)

        status = result.stdout.strip()
        if status == "healthy":
            print(f"Container '{container_name}' is healthy!")
            return
        elif status == "unhealthy":
            raise RuntimeError(f"Container '{container_name}' became unhealthy!")

        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timeout waiting for container '{container_name}' to become healthy.")

        time.sleep(2)


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

def fetch_admin_init_password() -> str:
    cmd = ["sudo", "docker", "exec", "dom-cli-domserver", "cat", "/opt/domjudge/domserver/etc/initial_admin_password.secret"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    pattern = re.compile(r"^\S+$", re.MULTILINE)

    match = pattern.search(result.stdout.strip())
    if not match:
        raise ValueError("Failed to parse admin initial password from output")

    password = match.group(0)
    return password


def update_admin_password(new_password: str, db_user: str, db_password: str) -> None:
    """
    Securely update the admin password in the DOMjudge database.
    """
    hashed_password = generate_bcrypt_password(new_password)

    sql_query = (
        f"USE domjudge; "
        f"UPDATE user SET password='{hashed_password}' WHERE username='admin';"
    )

    cmd = [
        "sudo", "docker", "exec", "-e", f"MYSQL_PWD={db_password}",
        "dom-cli-mysql-client",
        "mysql",
        "-h", "dom-cli-mariadb",
        "-u", db_user,
        "-e", sql_query
    ]

    subprocess.run(cmd, check=True)
    print("✅ Admin password successfully updated.")

