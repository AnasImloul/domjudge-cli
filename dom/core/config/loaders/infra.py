from dom.types.config.raw import RawInfraConfig
from dom.types.config.processed import InfraConfig


def load_infra_from_config(infra: RawInfraConfig) -> InfraConfig:
    return InfraConfig(
        port=infra.port,
        judges=infra.judges,
        password=infra.password.get_secret_value()
    )