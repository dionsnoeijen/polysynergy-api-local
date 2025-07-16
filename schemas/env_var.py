from pydantic import BaseModel


class EnvVarStageValue(BaseModel):
    id: str
    value: str


class EnvVarOut(BaseModel):
    key: str
    values: dict[str, EnvVarStageValue]


class EnvVarCreateIn(BaseModel):
    key: str
    value: str
    stage: str