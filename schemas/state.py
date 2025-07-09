from pydantic import BaseModel, field_validator
import re

CAMELCASE_REGEX = re.compile(r"^[a-z]+(?:[A-Z][a-z0-9]+)*$")

class StateIn(BaseModel):
    key: str
    value: dict | str | int | float | bool | None

    @field_validator("key", mode="before")
    def key_must_be_camelcase(cls, v):
        if not isinstance(v, str) or not CAMELCASE_REGEX.match(v):
            raise ValueError("Key must be lowerCamelCase")
        return v


class StateOut(BaseModel):
    key: str
    value: dict | str | int | float | bool | None