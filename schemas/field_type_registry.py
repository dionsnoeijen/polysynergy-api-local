"""Field Type Registry schemas"""

from pydantic import BaseModel
from typing import Optional


class FieldTypeRead(BaseModel):
    """Schema for reading field types from runtime loader"""
    handle: str
    label: str
    postgres_type: str
    ui_component: str
    category: str = "general"
    icon: Optional[str] = None
    settings_schema: Optional[dict] = None
    version: Optional[str] = None
