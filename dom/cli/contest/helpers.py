"""Helper functions for contest CLI commands."""

from pathlib import Path

from dom.core.operations import Context, run
from dom.core.operations.contest import load_config_op
from dom.utils.cli import get_secrets_manager


def load_config_with_secrets(file: Path | None, verbose: bool = False):
    """Load contest configuration with the secrets manager.

    Returns ``(DomConfig, SecretsManager)``. Raises ``typer.Exit(1)`` on failure.
    """
    secrets = get_secrets_manager()
    ctx = Context(secrets=secrets, verbose=verbose)
    config = run(load_config_op(file), ctx)
    return config, secrets
