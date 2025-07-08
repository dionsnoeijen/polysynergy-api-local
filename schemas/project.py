from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    tenant_id: str