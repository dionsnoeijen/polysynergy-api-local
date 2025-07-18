from pydantic import BaseModel
from datetime import datetime

class ApiKeyOut(BaseModel):
    key_id: str
    tenant_id: str
    project_id: str
    label: str
    key: str
    type: str
    created_at: datetime

class ApiKeyCreateIn(BaseModel):
    label: str
    key: str

class ApiKeyUpdateIn(BaseModel):
    label: str