import os

from dom.infrastructure.docker.template import generate_docker_compose
from dom.infrastructure.docker.containers import (
    start_services,
    fetch_judgedaemon_password,
    wait_for_container_healthy,
    fetch_admin_init_password,
    update_admin_password,
)
from dom.types.infra import InfraConfig
from dom.infrastructure.secrets.manager import (
    load_or_default_secret,
    load_secret,
    save_secret,
)
from dom.utils.cli import ensure_dom_directory


def apply_infra_and_platform(infra_config: InfraConfig) -> None:
    compose_file = os.path.join(ensure_dom_directory(), "docker-compose.yml")

    print("Step 1: Generating initial docker-compose...")
    generate_docker_compose(infra_config, judge_password="TEMP")

    print("Step 2: Starting core services (MariaDB + Domserver + MySQL Client)...")
    start_services(["mariadb", "mysql-client", "domserver"], compose_file)

    print("Waiting for Domserver to be healthy...")
    wait_for_container_healthy("dom-cli-domserver")

    print("Step 3: Fetching judgedaemon password...")
    judge_password = fetch_judgedaemon_password()

    print("Step 4: Regenerating docker-compose with real judgedaemon password...")
    generate_docker_compose(infra_config, judge_password=judge_password)

    print("Step 5: Starting judgehosts...")
    judgehost_services = [f"judgehost-{i + 1}" for i in range(infra_config.judges)]
    start_services(judgehost_services, compose_file)

    print("Step 6: Updating admin password...")
    admin_password = (
        infra_config.password.get_secret_value() if infra_config.password else None
        or load_or_default_secret("admin_password")
        or fetch_admin_init_password()
    )

    update_admin_password(
        new_password=admin_password,
        db_user="domjudge",
        db_password=load_secret("db_password"),
    )
    save_secret("admin_password", admin_password)

    print("✅ Infrastructure and platform are ready!")
