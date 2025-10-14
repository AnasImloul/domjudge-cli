from pydantic import BaseModel, SecretStr

from dom.utils.pydantic import InspectMixin


class Team(InspectMixin, BaseModel):
    id: str | None = None
    name: str
    affiliation: str | None = None
    username: str | None = None
    password: SecretStr
