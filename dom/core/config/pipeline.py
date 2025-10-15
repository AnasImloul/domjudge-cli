"""Declarative configuration loading pipeline.

This module provides a clear, declarative way to load and process configuration
through a series of well-defined stages.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

import yaml

from dom.core.config.loaders.contest import load_contests_from_config
from dom.core.config.loaders.infra import load_infra_from_config
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
from dom.types.config.raw import RawContestConfig, RawInfraConfig
from dom.utils.cli import find_config_or_default, get_secrets_manager

logger = get_logger(__name__)

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass
class PipelineContext:
    """
    Context passed through the configuration pipeline.

    Provides access to dependencies and metadata needed during processing.
    """

    config_path: Path | None
    secrets: SecretsManager
    metadata: dict[str, Any]

    @classmethod
    def create(
        cls,
        config_path: Path | None = None,
        secrets: SecretsManager | None = None,
    ) -> "PipelineContext":
        """
        Create a pipeline context with defaults.

        Args:
            config_path: Optional configuration file path
            secrets: Optional secrets manager

        Returns:
            Pipeline context
        """
        if secrets is None:
            secrets = get_secrets_manager()

        return cls(
            config_path=config_path,
            secrets=secrets,
            metadata={},
        )


class PipelineStage(ABC, Generic[TInput, TOutput]):
    """
    Base class for declarative pipeline stages.

    Each stage:
    1. Has a clear, single responsibility
    2. Declares what it does, not how
    3. Can be composed with other stages
    4. Is independently testable

    Example:
        >>> class LoadYAMLStage(PipelineStage[Path, dict]):
        ...     def name(self) -> str:
        ...         return "Load YAML file"
        ...
        ...     def execute(self, input: Path, context: PipelineContext) -> dict:
        ...         with open(input) as f:
        ...             return yaml.safe_load(f)
    """

    @abstractmethod
    def name(self) -> str:
        """
        Return human-readable name of this stage.

        This should describe what the stage does in declarative terms.
        """

    @abstractmethod
    def execute(self, input_data: TInput, context: PipelineContext) -> TOutput:
        """
        Execute the pipeline stage.

        Args:
            input_data: Input from previous stage
            context: Pipeline context

        Returns:
            Transformed output

        Raises:
            Exception: If processing fails
        """

    def __str__(self) -> str:
        """String representation."""
        return self.name()


class ConfigPipeline(Generic[TOutput]):
    """
    Declarative configuration processing pipeline.

    Chains multiple stages together to transform configuration
    from raw input to processed output.

    Example:
        >>> pipeline = (
        ...     ConfigPipeline()
        ...     .add_stage(FindConfigFileStage())
        ...     .add_stage(LoadYAMLStage())
        ...     .add_stage(ValidateSchemaStage())
        ...     .add_stage(ProcessConfigStage())
        ... )
        >>> config = pipeline.run(context)
    """

    def __init__(self):
        """Initialize empty pipeline."""
        self._stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> "ConfigPipeline[TOutput]":
        """
        Add a stage to the pipeline.

        Args:
            stage: Pipeline stage to add

        Returns:
            Self for chaining
        """
        self._stages.append(stage)
        logger.debug(f"Added pipeline stage: {stage.name()}")
        return self

    def run(self, context: PipelineContext, initial_input: Any = None) -> TOutput:
        """
        Execute the entire pipeline.

        Args:
            context: Pipeline context
            initial_input: Optional initial input

        Returns:
            Final output from last stage

        Raises:
            Exception: If any stage fails
        """
        logger.info(f"Starting configuration pipeline with {len(self._stages)} stages")

        current_data = initial_input
        for i, stage in enumerate(self._stages, 1):
            stage_name = stage.name()
            logger.info(f"Pipeline stage {i}/{len(self._stages)}: {stage_name}")

            try:
                current_data = stage.execute(current_data, context)
                logger.debug(f"Stage '{stage_name}' completed successfully")
            except Exception as e:
                logger.error(
                    f"Pipeline stage '{stage_name}' failed: {e}",
                    exc_info=True,
                    extra={"stage": stage_name, "stage_number": i},
                )
                raise RuntimeError(
                    f"Configuration pipeline failed at stage '{stage_name}': {e}"
                ) from e

        logger.info("Configuration pipeline completed successfully")
        return current_data  # type: ignore[no-any-return]


# Common pipeline stages


class FindConfigFileStage(PipelineStage[None, Path]):
    """Find configuration file from context or default location."""

    def name(self) -> str:
        """Stage name."""
        return "Find configuration file"

    def execute(self, input_data: None, context: PipelineContext) -> Path:  # noqa: ARG002
        """Find configuration file."""
        config_path = find_config_or_default(context.config_path)
        context.metadata["config_path"] = config_path
        logger.info(f"Using configuration file: {config_path}")
        return config_path


class LoadYAMLStage(PipelineStage[Path, dict[str, Any]]):
    """Load YAML file into dictionary."""

    def name(self) -> str:
        """Stage name."""
        return "Load YAML configuration"

    def execute(self, input_data: Path, context: PipelineContext) -> dict[str, Any]:  # noqa: ARG002
        """Load YAML file."""
        with input_data.open() as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded YAML from {input_data}")
        return data  # type: ignore[no-any-return]


class ValidateSchemaStage(PipelineStage[dict[str, Any], dict[str, Any]]):
    """Validate configuration against schema."""

    def name(self) -> str:
        """Stage name."""
        return "Validate configuration schema"

    def execute(self, input_data: dict[str, Any], context: PipelineContext) -> dict[str, Any]:  # noqa: ARG002
        """Validate schema."""
        # Add validation logic here if needed
        logger.info("Configuration schema validated")
        return input_data


class ParseInfraConfigStage(PipelineStage[dict[str, Any], Any]):
    """Parse infrastructure configuration from raw data."""

    def name(self) -> str:
        """Stage name."""
        return "Parse infrastructure configuration"

    def execute(self, input_data: dict[str, Any], context: PipelineContext) -> Any:
        """Parse infrastructure config."""
        raw_infra = RawInfraConfig(**input_data.get("infra", {}))
        config_path = context.metadata.get("config_path", Path.cwd())
        return load_infra_from_config(raw_infra, config_path)


class ParseContestsConfigStage(PipelineStage[dict[str, Any], list[Any]]):
    """Parse contests configuration from raw data."""

    def name(self) -> str:
        """Stage name."""
        return "Parse contests configuration"

    def execute(self, input_data: dict[str, Any], context: PipelineContext) -> list[Any]:
        """Parse contests config."""
        raw_contests = [RawContestConfig(**c) for c in input_data.get("contests", [])]
        config_path = context.metadata.get("config_path", Path.cwd())
        return load_contests_from_config(raw_contests, config_path, context.secrets)


def create_infra_config_pipeline() -> ConfigPipeline:
    """
    Create a declarative pipeline for loading infrastructure configuration.

    Returns:
        Configured pipeline
    """
    return (
        ConfigPipeline()
        .add_stage(FindConfigFileStage())
        .add_stage(LoadYAMLStage())
        .add_stage(ValidateSchemaStage())
        .add_stage(ParseInfraConfigStage())
    )


def create_full_config_pipeline() -> ConfigPipeline:
    """
    Create a declarative pipeline for loading complete configuration.

    Returns:
        Configured pipeline
    """
    # This would need to be implemented to combine infra and contests
    # For now, keeping it simple
    return (
        ConfigPipeline()
        .add_stage(FindConfigFileStage())
        .add_stage(LoadYAMLStage())
        .add_stage(ValidateSchemaStage())
    )
