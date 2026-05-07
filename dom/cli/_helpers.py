"""Shared CLI helpers.

Both contest and infrastructure CLI commands need the same shape:
build a ``SecretsManager``, build a ``Context``, run a configuration
load operation. Parameterizing on the operation factory collapses the
two duplicate ``helpers.py`` modules into one.
"""

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from dom.core.operations import Context, run
from dom.core.operations.framework import Operation
from dom.types.secrets import SecretsProvider
from dom.utils.cli import get_secrets_manager

T = TypeVar("T")

ConfigOpFactory = Callable[[Path | None], Operation[T]]


def load_with_secrets(
    config_op_factory: ConfigOpFactory[T],
    file: Path | None,
    verbose: bool = False,
) -> tuple[T, SecretsProvider]:
    """Run a configuration-loading operation and return ``(config, secrets)``.

    ``config_op_factory`` is one of the ``load_*_op`` factories (e.g.
    ``load_config_op``, ``load_infra_config_op``). It's called with
    ``file`` to produce the bound :class:`Operation`. Raises
    ``typer.Exit(1)`` on failure (propagated from :func:`run`).
    """
    secrets = get_secrets_manager()
    config = run(config_op_factory(file), Context(secrets=secrets, verbose=verbose))
    if config is None:
        raise RuntimeError(
            f"{config_op_factory.__name__} returned no value; "
            "load operations must be single-step and produce a config object"
        )
    return config, secrets
