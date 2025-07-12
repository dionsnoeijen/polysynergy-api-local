from pydantic import BaseModel, EmailStr
from uuid import UUID

class TenantUserOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None

    model_config = {"from_attributes": True}
