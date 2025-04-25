from dom.infrastructure.docker.template import generate_docker_compose
from dom.infrastructure.docker.containers import start_services, fetch_judgedaemon_password
from dom.infrastructure.api import sync_contests
import time


def apply_infra_and_platform(config: dict) -> None:
    print("Step 1: Generating docker-compose for mariadb + domserver...")
    generate_docker_compose(config, judge_password="TEMP")

    print("Step 2: Starting mariadb and domserver...")
    infra = config.get("infra", {})

    compose_file = "./api/docker-compose.yml"
    start_services(["mariadb", "domserver"], compose_file)

    print("Waiting for domserver to be ready...")
    time.sleep(10)

    print("Step 3: Fetching judgedaemon password...")
    judge_password = fetch_judgedaemon_password()

    print("Step 4: Regenerating docker-compose with real judgedaemon password...")
    generate_docker_compose(config, judge_password=judge_password)

    print("Step 5: Starting judgehosts...")
    judge_count = infra.get("judgehost_count", 1)
    start_services([f"judgehost-{i+1}" for i in range(judge_count)], compose_file)

    print("Step 6: Syncing contests...")
    sync_contests(config.get("contests", []))
    print("Infrastructure and platform ready!")
