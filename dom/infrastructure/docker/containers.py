from typing import List
import time
import re
import subprocess
from dom.utils.hash import generate_bcrypt_password

DOCKER_CMD = None

def docker_prefix() -> List[str]:
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return ["docker"]
    except subprocess.CalledProcessError:
        raise PermissionError(
            "You don't have permission to run 'docker'. "
            "Please run this command with 'sudo' (e.g., 'sudo dom infra apply') or fix your docker permissions."
        )

def start_services(services: List[str], compose_file: str) -> None:
    global DOCKER_CMD
    if DOCKER_CMD is None:
        DOCKER_CMD = docker_prefix()
    cmd = DOCKER_CMD + ["compose", "-f", compose_file, "up", "-d", "--remove-orphans"] + services
    subprocess.run(cmd, check=True)

def stop_all_services(compose_file: str) -> None:
    global DOCKER_CMD
    if DOCKER_CMD is None:
        DOCKER_CMD = docker_prefix()
    cmd = DOCKER_CMD + ["compose", "-f", compose_file, "down", "-v"]
    subprocess.run(cmd, check=True)

def wait_for_container_healthy(container_name: str, timeout: int = 60) -> None:
    global DOCKER_CMD
    if DOCKER_CMD is None:
        DOCKER_CMD = docker_prefix()

    start_time = time.time()

    while True:
        cmd = DOCKER_CMD + ["inspect", "--format={{.State.Health.Status}}", container_name]
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
    global DOCKER_CMD
    if DOCKER_CMD is None:
        DOCKER_CMD = docker_prefix()
    cmd = DOCKER_CMD + ["exec", "dom-cli-domserver", "cat", "/opt/domjudge/domserver/etc/restapi.secret"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    pattern = re.compile(r"^\S+\s+\S+\s+\S+\s+(\S+)$", re.MULTILINE)
    match = pattern.search(result.stdout.strip())
    if not match:
        raise ValueError("Failed to parse judgedaemon password from output")

    return match.group(1)

def fetch_admin_init_password() -> str:
    global DOCKER_CMD
    if DOCKER_CMD is None:
        DOCKER_CMD = docker_prefix()
    cmd = DOCKER_CMD + ["exec", "dom-cli-domserver", "cat", "/opt/domjudge/domserver/etc/initial_admin_password.secret"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    pattern = re.compile(r"^\S+$", re.MULTILINE)
    match = pattern.search(result.stdout.strip())
    if not match:
        raise ValueError("Failed to parse admin initial password from output")

    return match.group(0)

def update_admin_password(new_password: str, db_user: str, db_password: str) -> None:
    global DOCKER_CMD
    if DOCKER_CMD is None:
        DOCKER_CMD = docker_prefix()

    hashed_password = generate_bcrypt_password(new_password)

    sql_query = (
        f"USE domjudge; "
        f"UPDATE user SET password='{hashed_password}' WHERE username='admin';"
    )

    cmd = DOCKER_CMD + [
        "exec", "-e", f"MYSQL_PWD={db_password}",
        "dom-cli-mysql-client",
        "mysql",
        "-h", "dom-cli-mariadb",
        "-u", db_user,
        "-e", sql_query
    ]

    subprocess.run(cmd, check=True)
    print("✅ Admin password successfully updated.")
