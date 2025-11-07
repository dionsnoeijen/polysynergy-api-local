"""Field schemas - for reusable field library"""

from pydantic import BaseModel, Field as PydanticField
from uuid import UUID
from datetime import datetime
from typing import Optional


class FieldCreate(BaseModel):
    """Schema for creating a field in the field library"""
    handle: str = PydanticField(..., max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    label: str = PydanticField(..., max_length=200)
    field_type_handle: str = PydanticField(..., max_length=100)

    # Field configuration
    field_settings: dict = PydanticField(default_factory=dict)
    default_value: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = PydanticField(None, max_length=200)

    # Validation
    is_required: bool = False
    is_unique: bool = False
    custom_validation_rules: Optional[dict] = None

    # For relation fields
    related_section_id: Optional[UUID] = None


class FieldUpdate(BaseModel):
    """Schema for updating a field"""
    label: Optional[str] = PydanticField(None, max_length=200)
    field_settings: Optional[dict] = None
    default_value: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = PydanticField(None, max_length=200)
    is_required: Optional[bool] = None
    is_unique: Optional[bool] = None
    custom_validation_rules: Optional[dict] = None
    related_section_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


class FieldRead(BaseModel):
    """Schema for reading a field"""
    id: UUID
    project_id: UUID
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
    related_section_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
