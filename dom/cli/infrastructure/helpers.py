"""Helper functions for infrastructure CLI commands."""

from pathlib import Path
from typing import Any

import typer

from dom.cli.helpers import get_secrets_manager
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.infrastructure import LoadInfraConfigOperation


def load_infra_config_with_secrets(file: Path | None, verbose: bool = False) -> Any:
    """
    Load infrastructure configuration file with secrets manager.

    This is a common pattern used across CLI commands to load infrastructure
    configuration with proper error handling.

    Args:
        file: Optional path to config file
        verbose: Enable verbose logging

    Returns:
        Tuple of (Loaded InfraConfig, SecretsManager)

    Raises:
        typer.Exit: If loading fails
    """
    secrets = get_secrets_manager()
    load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    load_runner = OperationRunner(LoadInfraConfigOperation(file))
    load_result = load_runner.run(load_context)

    if not load_result.is_success():
        raise typer.Exit(code=1)

    return load_result.unwrap(), secrets
