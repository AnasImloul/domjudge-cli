from dom.infrastructure.docker import stop_all_services

def destroy_infra_and_platform() -> None:
    print("🔥 DESTROY: Tearing down infrastructure...")

    compose_file = "./api/docker-compose.yml"

    stop_all_services(compose_file=compose_file)

    print("🔥 DESTROY: Clean-up done.")
