from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class ProjectTemplateCreate(BaseModel):
    """Schema for creating a new project template."""
    name: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    content: str = Field(default="")


class ProjectTemplateUpdate(BaseModel):
    """Schema for updating an existing project template."""
    name: str | None = Field(None, min_length=1, max_length=255, pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    content: str | None = None

    model_config = {"from_attributes": True}


class ProjectTemplateRead(BaseModel):
    """Schema for reading a project template."""
    id: UUID
    project_id: UUID
    name: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
