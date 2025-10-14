from dom.templates.base import get

contest_template = get("init/contest.yml.j2")
infra_template = get("init/infra.yml.j2")
problems_template = get("init/problems.yml.j2")

__all__ = ["contest_template", "infra_template", "problems_template"]
