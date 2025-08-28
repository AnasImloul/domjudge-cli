from functools import lru_cache
from jinja2 import Environment, PackageLoader, select_autoescape, Template

_env = Environment(
    loader=PackageLoader("dom", "templates"),
    autoescape=select_autoescape(),
    auto_reload=False,
    enable_async=False,
)

@lru_cache(maxsize=None)
def get(name: str) -> Template:
    """Return a cached Template by path (e.g., 'init/contest.yml.j2')."""
    return _env.get_template(name)

