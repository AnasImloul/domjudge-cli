from datetime import datetime
from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field, SecretStr, field_validator

from dom.validation import ValidationRules, for_pydantic, optional_for_pydantic
from dom.validation.adapters import for_prompt


class RawInfraConfig(BaseModel):
    port: int = 12345
    judges: int = 1
    password: SecretStr | None = None

    # Use centralized validation rules
    validate_port = field_validator("port")(for_pydantic(ValidationRules.port()))
    validate_judges = field_validator("judges")(for_pydantic(ValidationRules.judges_count()))

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr | None) -> SecretStr | None:
        """Validate password meets minimum requirements."""
        if v is None:
            return v
        # Validate the unwrapped value

        validator = for_prompt(ValidationRules.password())
        password_str = v.get_secret_value()
        try:
            validator(password_str)
        except Exception as e:
            raise ValueError(str(e)) from e
        return v

    class Config:
        frozen = True


class RawProblemsConfig(BaseModel):
    from_: str = Field(alias="from")

    class Config:
        frozen = True
        populate_by_name = True


class RawProblem(BaseModel):
    archive: str
    platform: str
    color: str

    class Config:
        frozen = True


class RawTeamsConfig(BaseModel):
    from_: str = Field(alias="from")
    delimiter: str | None = None
    rows: str
    name: str
    affiliation: str

    class Config:
        frozen = True
        populate_by_name = True


class RawContestConfig(BaseModel):
    name: str
    shortname: str | None = None
    formal_name: str | None = None
    start_time: datetime | None = None
    duration: str | None = None
    penalty_time: int = 0
    allow_submit: bool = True
    with_statement: bool = False

    problems: Union[RawProblemsConfig, list[RawProblem]]
    teams: RawTeamsConfig

    # Use centralized validation rules
    validate_name = field_validator("name")(for_pydantic(ValidationRules.contest_name()))
    validate_shortname = field_validator("shortname")(
        optional_for_pydantic(ValidationRules.contest_shortname())
    )
    validate_penalty_time = field_validator("penalty_time")(
        for_pydantic(ValidationRules.penalty_time())
    )
    validate_duration = field_validator("duration")(
        optional_for_pydantic(ValidationRules.duration())
    )

    class Config:
        frozen = True


class RawDomConfig(BaseModel):
    infra: RawInfraConfig = RawInfraConfig()
    contests: list[RawContestConfig] = []  # Always a list, never None
    loaded_from: Path

    class Config:
        frozen = True
