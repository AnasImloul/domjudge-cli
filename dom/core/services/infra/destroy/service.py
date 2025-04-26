import os
from dom.infrastructure.docker import stop_all_services
from dom.utils.cli import ensure_dom_directory
from dom.infrastructure.secrets.manager import clear_secrets


def destroy_infra_and_platform() -> None:
    print("🔥 DESTROY: Tearing down infrastructure...")
    compose_file = os.path.join(ensure_dom_directory(), "docker-compose.yml")

    stop_all_services(compose_file=compose_file)
    clear_secrets()
    print("🔥 DESTROY: Clean-up done.")
