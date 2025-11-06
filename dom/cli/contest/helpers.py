"""Helper functions for contest CLI commands."""

from pathlib import Path

import typer

from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.contest import LoadConfigOperation
from dom.utils.cli import get_secrets_manager


def load_config_with_secrets(file: Path | None, verbose: bool = False):
    """
    Load contest configuration file with secrets manager.

    This is a common pattern used across CLI commands to load configuration
    with proper error handling.

    Args:
        file: Optional path to config file
        verbose: Enable verbose logging

    Returns:
        Tuple of (Loaded DomConfig, SecretsManager)

    Raises:
        typer.Exit: If loading fails
    """
    secrets = get_secrets_manager()
    load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    load_runner = OperationRunner(LoadConfigOperation(file))
    load_result = load_runner.run(load_context)

    if not load_result.is_success():
        raise typer.Exit(code=1)

    return load_result.unwrap(), secrets
