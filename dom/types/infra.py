from pydantic import BaseModel, SecretStr

from dom.utils.pydantic import InspectMixin


class InfraConfig(InspectMixin, BaseModel):
    port: int = 12345
    judges: int = 1
    password: SecretStr | None = None

    class Config:
        frozen = True
