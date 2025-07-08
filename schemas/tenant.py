from pydantic import BaseModel

class TenantCreate(BaseModel):
    name: str