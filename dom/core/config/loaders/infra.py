from dom.types.config.processed import InfraConfig
from dom.types.config.raw import RawInfraConfig


def load_infra_from_config(infra: RawInfraConfig, config_path: str | None = None) -> InfraConfig:
    _ = config_path  # Reserved for future use
    return InfraConfig(
        port=infra.port,
        judges=infra.judges,
        password=infra.password.get_secret_value() if infra.password else None,  # type: ignore[arg-type]
    )
