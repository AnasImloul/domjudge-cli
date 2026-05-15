"""Resolve a ``RawProblemsConfig`` (or inline list) to a list of ``RawProblem``.

This is the file-lookup half of ``load_problems_from_config``: figure
out where the problems list lives on disk (or accept it inline), load
it, and return a normalized list. Validation of archive paths and
parallel loading happen in the caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from dom.logging_config import get_logger
from dom.types.config.raw import RawProblem, RawProblemsConfig
from dom.utils.project import find_file_with_extensions

logger = get_logger(__name__)


def resolve_problems_list(
    problem_config: Union[RawProblemsConfig, list[RawProblem]],
    config_path: Path,
) -> list[RawProblem]:
    """Return the list of ``RawProblem`` entries to load.

    Accepts either an inline list or a ``RawProblemsConfig`` whose
    ``from_`` field points at a YAML file (explicit) or directory
    (default-lookup).
    """
    if isinstance(problem_config, list):
        return problem_config

    if not isinstance(problem_config, RawProblemsConfig):
        logger.error("Invalid problem configuration.")
        raise TypeError("Invalid problem configuration type.")

    file_path = _resolve_problems_file(problem_config, config_path)

    try:
        with file_path.open() as f:
            loaded_data = yaml.safe_load(f)
        if not isinstance(loaded_data, list):
            logger.error(f"Problems file '{file_path}' must contain a list.")
            raise ValueError(f"Problems file must contain a list of problems: {file_path}")
        return [RawProblem(**problem) for problem in loaded_data]
    except (OSError, yaml.YAMLError, ValueError, TypeError):
        logger.error(f"Failed to load problems from '{file_path}'", exc_info=True)
        raise


def _resolve_problems_file(cfg: RawProblemsConfig, config_path: Path) -> Path:
    """Locate the problems YAML file based on ``cfg.from_`` (or default)."""
    config_dir = config_path.resolve().parent

    if cfg.from_ is None:
        try:
            return find_file_with_extensions(
                base_path=config_dir,
                base_name="problems",
                error_context="No 'from' path provided and no default problems file found.",
            )
        except FileNotFoundError as e:
            logger.error(str(e))
            raise

    from_path = config_dir / cfg.from_

    if from_path.suffix.lower() in (".yml", ".yaml"):
        if not from_path.exists():
            logger.error(f"Problems file '{from_path}' does not exist.")
            raise FileNotFoundError(f"Problems file not found: {from_path}")
        return from_path

    try:
        return find_file_with_extensions(
            base_path=from_path,
            base_name="problems",
            error_context=f"No problems.yaml or problems.yml found in '{from_path}'.",
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        raise
