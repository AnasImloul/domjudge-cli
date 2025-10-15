"""DOMjudge CLI - CLI tool for managing DOMjudge contests and infrastructure."""

# Single source of truth for version: pyproject.toml
# This reads from installed package metadata when available
try:
    from importlib.metadata import version

    __version__ = version("domjudge-cli")
except Exception:
    # Fallback for development/editable installs: read from pyproject.toml
    from pathlib import Path

    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)
        __version__ = pyproject_data["project"]["version"]
    except Exception:
        # Last resort fallback
        __version__ = "0.0.0-dev"
