"""Helper functions for infrastructure CLI commands."""

from pathlib import Path

from dom.cli._helpers import load_with_secrets
from dom.core.operations.infrastructure import load_infra_config_op


def load_infra_config_with_secrets(file: Path | None, verbose: bool = False):
    """Load infrastructure configuration with the secrets manager.

    Returns ``(InfraConfig, SecretsManager)``. Raises ``typer.Exit(1)`` on failure.
    """
    return load_with_secrets(load_infra_config_op, file, verbose)
