from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)

class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    model_config = {"from_attributes": True}

class ProjectRead(BaseModel):
    id: UUID
    name: str
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}