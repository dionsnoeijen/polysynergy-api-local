"""Field Type Registry schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class FieldTypeRegistryRead(BaseModel):
    """Schema for reading field type registry"""
    id: UUID
    handle: str
    label: str
    postgres_type: str
    ui_component: str
    category: str
    icon: Optional[str] = None
    settings_schema: Optional[dict] = None
    version: Optional[str] = None
    registered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
