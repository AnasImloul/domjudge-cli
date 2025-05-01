from jinja2 import Environment, PackageLoader, select_autoescape
import os
from dom.cli import console

from dom.infrastructure.secrets.manager import load_or_generate_secret
from dom.types.infra import InfraConfig
from dom.utils.cli import ensure_dom_directory

def generate_docker_compose(infra_config: InfraConfig, judge_password: str) -> None:
    dom_folder = ensure_dom_directory()

    output_file = os.path.join(dom_folder, "docker-compose.yml")

    env = Environment(
        loader=PackageLoader("dom", "templates"),
        autoescape=select_autoescape()
    )
    template = env.get_template("docker-compose.yml.j2")

    rendered = template.render(
        platform_port=infra_config.port,
        judgehost_count=infra_config.judges,
        judgedaemon_password=judge_password,
        db_password=load_or_generate_secret("db_password", length=16)
    )

    with open(output_file, "w") as f:
        f.write(rendered)

    console.print(f"[green]✅ Docker Compose file generated at {output_file}[/green]")
