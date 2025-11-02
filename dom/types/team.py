from pydantic import BaseModel, SecretStr, computed_field, field_validator

from dom.constants import DEFAULT_COUNTRY_CODE
from dom.utils.pydantic import InspectMixin


class Team(InspectMixin, BaseModel):
    id: str | None = None
    name: str
    affiliation: str | None = None
    country: str | None = None  # ISO 3166-1 alpha-3 country code
    username: str | None = None
    password: SecretStr

    @field_validator("country", mode="before")
    @classmethod
    def set_default_country(cls, v: str | None) -> str:
        """Set default country code if not specified."""
        return v if v is not None else DEFAULT_COUNTRY_CODE

    @computed_field  # type: ignore[prop-decorator]
    @property
    def composite_key(self) -> str:
        """
        Composite key uniquely identifying this team across contests.

        Teams are uniquely identified by the combination of:
        - name: Team display name
        - affiliation: Organization/institution
        - country: Country code

        This allows different organizations to have teams with the same name
        (e.g., "Team Alpha" from MIT vs "Team Alpha" from Oxford).

        Returns:
            Composite key string in format "name|affiliation|country"
        """
        return f"{self.name}|{self.affiliation or ''}|{self.country or ''}"
