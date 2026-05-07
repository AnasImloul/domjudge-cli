"""DOMjudge CLI - CLI tool for managing DOMjudge contests and infrastructure."""

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]


def _read_version() -> str:
    try:
        return version("domjudge-cli")
    except PackageNotFoundError:
        pass

    if tomllib is None:
        return "0.0.0-dev"

    try:
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject.open("rb") as f:
            return str(tomllib.load(f)["project"]["version"])
    except (OSError, KeyError):
        return "0.0.0-dev"


__version__ = _read_version()
