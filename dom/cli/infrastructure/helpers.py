"""Helper functions for infrastructure CLI commands."""

from pathlib import Path

from dom.core.operations import Context, run
from dom.core.operations.infrastructure import load_infra_config_op
from dom.utils.cli import get_secrets_manager


def load_infra_config_with_secrets(file: Path | None, verbose: bool = False):
    """Load infrastructure configuration with the secrets manager.

    Returns ``(InfraConfig, SecretsManager)``. Raises ``typer.Exit(1)`` on failure.
    """
    secrets = get_secrets_manager()
    ctx = Context(secrets=secrets, verbose=verbose)
    config = run(load_infra_config_op(file), ctx)
    return config, secrets
