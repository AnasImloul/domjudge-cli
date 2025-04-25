from jinja2 import Environment, PackageLoader, select_autoescape
import os


def generate_docker_compose(config: dict, judge_password: str) -> None:
    infra = config.get("infra", dict())

    os.makedirs("./api", exist_ok=True)

    output_file = "./api/docker-compose.yml"

    # ✅ Load Jinja2 template from package using PackageLoader
    env = Environment(
        loader=PackageLoader("dom", "templates"),
        autoescape=select_autoescape()
    )
    template = env.get_template("docker-compose.yml.j2")

    # ✅ Render template with variables
    rendered = template.render(
        platform_port=infra.get("platform_port", 12345),
        judgehost_count=infra.get("judgehost_count", 1),
        judgedaemon_password=judge_password,
    )

    # ✅ Write to file
    with open(output_file, "w") as f:
        f.write(rendered)

    print(f"✅ Docker Compose file api at {output_file}")
