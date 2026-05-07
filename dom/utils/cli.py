"""Cross-layer filesystem / project utilities.

These helpers are *not* CLI-specific even though the module name says
"cli". They're consumed by services and infrastructure (e.g.
``get_container_prefix``) as well as the CLI. UI-bearing decorators and
prompts live in :mod:`dom.cli.decorators` and :mod:`dom.cli.helpers`.
"""

from hashlib import sha256
from pathlib import Path

from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger

logger = get_logger(__name__)


def ensure_dom_directory() -> Path:
    """Ensure ``.dom`` exists in the current working directory and return it."""
    dom_path = Path.cwd() / ".dom"
    dom_path.mkdir(exist_ok=True)
    return dom_path


def get_container_prefix() -> str:
    """Generate a unique container prefix derived from the current working directory.

    Allows multiple DOMjudge instances to coexist on one host; the
    prefix is a deterministic short hash of the absolute CWD path.
    """
    cwd = Path.cwd().resolve()
    path_hash = sha256(str(cwd).encode()).hexdigest()[:6]
    return f"domjudge-{path_hash}"


def get_secrets_manager() -> SecretsManager:
    """Return a ``SecretsManager`` rooted at the current project's ``.dom`` directory."""
    return SecretsManager(ensure_dom_directory())


def find_file_with_extensions(
    base_path: Path | str,
    base_name: str,
    extensions: tuple[str, str] = (".yaml", ".yml"),
    error_context: str | None = None,
) -> Path:
    """Find ``base_name.yaml`` or ``base_name.yml``.

    Accepts an explicit file path (returned as-is if it exists), a
    directory (searched within), or a base name (searched in CWD).
    Raises if both extensions resolve to existing files.
    """
    base_path = Path(base_path)

    if base_path.is_file():
        return base_path

    search_dir = base_path if base_path.is_dir() else Path.cwd()

    ext1, ext2 = extensions
    path1 = search_dir / f"{base_name}{ext1}"
    path2 = search_dir / f"{base_name}{ext2}"

    if path1.is_file() and path2.is_file():
        raise FileExistsError(
            f"Both '{path1.name}' and '{path2.name}' exist in '{search_dir}'. "
            f"Please specify which one to use explicitly."
        )

    if path1.is_file():
        return path1
    if path2.is_file():
        return path2

    raise FileNotFoundError(
        f"No '{base_name}{ext1}' or '{base_name}{ext2}' found in '{search_dir}'. "
        f"{error_context or ''}"
    )


def find_config_or_default(file: Path | None) -> Path:
    """Return ``file`` if given, else search CWD for ``dom-judge.{yaml,yml}``."""
    if file:
        if not file.is_file():
            raise FileNotFoundError(f"Specified config file '{file}' not found.")
        return file

    return find_file_with_extensions(
        base_path=Path.cwd(),
        base_name="dom-judge",
        error_context="Please specify a config file with --file or run 'dom init' first.",
    )


def check_file_exists(file: Path) -> bool:
    """Raise ``FileExistsError`` if ``file`` exists; otherwise return ``False``."""
    if file.is_file():
        raise FileExistsError(
            f"File '{file}' already exists. "
            "Rename or remove the existing file, or use --overwrite to replace it."
        )
    return False
