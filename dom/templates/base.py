from functools import cache

from jinja2 import Environment, PackageLoader, Template, select_autoescape

_env = Environment(
    loader=PackageLoader("dom", "templates"),
    autoescape=select_autoescape(),
    auto_reload=False,
    enable_async=False,
)


@cache
def get(name: str) -> Template:
    """Return a cached Template by path (e.g., 'init/contest.yml.j2')."""
    return _env.get_template(name)
