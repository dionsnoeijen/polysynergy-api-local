"""Section Field schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class SectionFieldCreate(BaseModel):
    """Schema for creating section field"""
    section_id: UUID
    handle: str = Field(..., max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    label: str = Field(..., max_length=200)
    field_type_handle: str = Field(..., max_length=100)

    # Field configuration
    field_settings: dict = Field(default_factory=dict)
    default_value: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = Field(None, max_length=200)

    # Validation
    is_required: bool = False
    is_unique: bool = False
    custom_validation_rules: Optional[dict] = None

    # UI/Layout
    ui_width: str = Field(default="full", max_length=20)  # full, half, third, quarter
    tab_name: str = Field(default="Content", max_length=100)
    sort_order: int = 0
    is_visible: bool = True

    # For relation fields
    related_section_id: Optional[UUID] = None


class SectionFieldUpdate(BaseModel):
    """Schema for updating section field"""
    label: Optional[str] = Field(None, max_length=200)
    field_settings: Optional[dict] = None
    default_value: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = Field(None, max_length=200)
    is_required: Optional[bool] = None
    is_unique: Optional[bool] = None
    custom_validation_rules: Optional[dict] = None
    ui_width: Optional[str] = Field(None, max_length=20)
    tab_name: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    related_section_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


class SectionFieldRead(BaseModel):
    """Schema for reading section field"""
    id: UUID
    section_id: UUID
    handle: str
    label: str
    field_type_handle: str
    field_settings: dict
    default_value: Optional[str]
    help_text: Optional[str]
    placeholder: Optional[str]
    is_required: bool
    is_unique: bool
    custom_validation_rules: Optional[dict]
    ui_width: str
    tab_name: str
    sort_order: int
    is_visible: bool
    related_section_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
