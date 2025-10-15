from dom.templates.base import get

docker_compose_template = get("infra/docker-compose.yml.j2")

__all__ = ["docker_compose_template"]
