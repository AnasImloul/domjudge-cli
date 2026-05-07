"""Helper functions for contest CLI commands."""

from pathlib import Path

from dom.cli._helpers import load_with_secrets
from dom.core.operations.contest import load_config_op


def load_config_with_secrets(file: Path | None, verbose: bool = False):
    """Load contest configuration with the secrets manager.

    Returns ``(DomConfig, SecretsManager)``. Raises ``typer.Exit(1)`` on failure.
    """
    return load_with_secrets(load_config_op, file, verbose)
