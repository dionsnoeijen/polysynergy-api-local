from pydantic import BaseModel


class SecretCreateIn(BaseModel):
    key: str
    secret_value: str
    stage: str

class SecretUpdateIn(BaseModel):
    key: str
    secret_value: str
    stage: str

class SecretOut(BaseModel):
    key: str
    project_id: str
    stages: list[str]

class SecretDeleteResult(BaseModel):
    stage: str
    deleted: bool
    error: str | None = None

class SecretDeleteIn(BaseModel):
    key: str

class SecretDeleteOut(BaseModel):
    results: list[SecretDeleteResult]