from pydantic import BaseModel
from uuid import UUID

class SecretCreateIn(BaseModel):
    key: str
    secret_value: str
    stage: str

class SecretUpdateIn(BaseModel):
    secret_value: str

class SecretOut(BaseModel):
    id: UUID
    key: str
    stage: str
    decrypted: bool