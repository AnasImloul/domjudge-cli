from pathlib import Path

from dom.infrastructure.config import load_config as load_raw_config
from dom.types.config.processed import ContestConfig, DomConfig, InfraConfig
from dom.types.secrets import SecretsProvider

from .contest import load_contest_from_config, load_contests_from_config
from .infra import load_infra_from_config


def load_config(file_path: Path | None, secrets: SecretsProvider) -> DomConfig:
    """
    Load complete DOMjudge configuration.

    Args:
        file_path: Path to config file
        secrets: Secrets manager instance (required for dependency injection)

    Returns:
        Complete configuration
    """
    config = load_raw_config(file_path)
    return DomConfig(
        infra=load_infra_from_config(config.infra, config_path=config.loaded_from),
        contests=load_contests_from_config(
            config.contests,
            config_path=config.loaded_from,
            secrets=secrets,
        ),
        loaded_from=config.loaded_from,
    )


def load_infrastructure_config(file_path: Path | None) -> InfraConfig:
    """Load infrastructure configuration only."""
    config = load_raw_config(file_path)
    return load_infra_from_config(config.infra, config_path=config.loaded_from)


def load_contests_config(file_path: Path | None, secrets: SecretsProvider) -> list[ContestConfig]:
    """
    Load contests configuration.

    Args:
        file_path: Path to config file
        secrets: Secrets manager instance (required for dependency injection)

    Returns:
        List of contest configurations
    """
    config = load_raw_config(file_path)
    return load_contests_from_config(
        config.contests,
        config_path=config.loaded_from,
        secrets=secrets,
    )


def load_contest_config(
    file_path: Path | None, contest_name: str, secrets: SecretsProvider
) -> ContestConfig:
    """
    Load a specific contest configuration by name.

    Args:
        file_path: Path to config file
        contest_name: Shortname of the contest to load
        secrets: Secrets manager instance (required for dependency injection)

    Returns:
        Contest configuration

    Raises:
        ValueError: If no contests found in config
        KeyError: If contest with given name not found
    """
    config = load_raw_config(file_path)

    if not config.contests:
        raise ValueError(
            f"No contests found in the provided config file"
            f"{f' ({config.loaded_from})' if config.loaded_from else ''}."
        )

    for contest in config.contests:
        if contest.shortname == contest_name:
            return load_contest_from_config(
                contest, config_path=config.loaded_from, secrets=secrets
            )

    available_contests = [contest.shortname for contest in config.contests]
    available_str = ", ".join(f"'{contest}'" for contest in available_contests)
    raise KeyError(
        f"Contest with name '{contest_name}' wasn't found in the config file"
        f"{f' ({config.loaded_from})' if config.loaded_from else ''}. "
        f"Available contests: {available_str}"
    )
