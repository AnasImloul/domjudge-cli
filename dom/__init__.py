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
        import sys

        # Python 3.11+ has tomllib built-in
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            # Python 3.10 needs tomli package
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                # If tomli not available, use fallback
                __version__ = "0.0.0-dev"
                tomllib = None  # type: ignore[assignment]

        if tomllib is not None:
            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)
            __version__ = pyproject_data["project"]["version"]
    except Exception:
        # Last resort fallback
        __version__ = "0.0.0-dev"
