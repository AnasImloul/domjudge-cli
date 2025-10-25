from dom.logging_config import get_logger
from dom.templates.infra import docker_compose_template
from dom.types.infra import InfraConfig
from dom.types.secrets import SecretsProvider
from dom.utils.cli import ensure_dom_directory, get_container_prefix

logger = get_logger(__name__)


def generate_docker_compose(
    infra_config: InfraConfig, secrets: SecretsProvider, judge_password: str
) -> None:
    """
    Generate docker-compose.yml file from template.

    Args:
        infra_config: Infrastructure configuration
        secrets: Secrets manager for retrieving credentials
        judge_password: Password for judgedaemon authentication
    """
    dom_folder = ensure_dom_directory()
    output_file = dom_folder / "docker-compose.yml"

    # Get unique container prefix for this directory
    container_prefix = get_container_prefix()

    rendered = docker_compose_template.render(
        container_prefix=container_prefix,
        platform_port=infra_config.port,
        judgehost_count=infra_config.judges,
        judgedaemon_password=judge_password,
        db_password=secrets.generate_and_store("db_password", length=16),
    )

    output_file.write_text(rendered)

    logger.info(f"Docker Compose file generated at {output_file} with prefix '{container_prefix}'")
