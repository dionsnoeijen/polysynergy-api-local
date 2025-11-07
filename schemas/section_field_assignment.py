"""Section Field Assignment schemas - for many-to-many relationship"""

from pydantic import BaseModel, Field as PydanticField
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class SectionFieldAssignmentCreate(BaseModel):
    """Schema for assigning a field to a section"""
    field_id: UUID
    section_id: UUID

    # Layout/UI Configuration
    # Note: Form layout (width, position) is stored in Section.layout_config
    tab_name: str = PydanticField(default="Content", max_length=100)
    sort_order: int = 0
    is_visible: bool = True

    # Can override field's is_required setting
    is_required_override: bool = False


class SectionFieldAssignmentUpdate(BaseModel):
    """Schema for updating a field assignment"""
    tab_name: Optional[str] = PydanticField(None, max_length=100)
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    is_required_override: Optional[bool] = None

    model_config = {"from_attributes": True}


class SectionFieldAssignmentRead(BaseModel):
    """Schema for reading a field assignment"""
    id: UUID
    section_id: UUID
    field_id: UUID
    tab_name: str
    sort_order: int
    is_visible: bool
    is_required_override: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionFieldAssignmentWithFieldRead(BaseModel):
    """Schema for reading a field assignment with complete field details"""
    id: UUID
    section_id: UUID
    field_id: UUID

    # Layout configuration from assignment
    # Note: Form layout (width, position) is stored in Section.layout_config
    tab_name: str
    sort_order: int
    is_visible: bool
    is_required_override: bool

    # Field details
    field_handle: str
    field_label: str
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


class BulkAssignmentCreate(BaseModel):
    """Schema for bulk assigning multiple fields to a section"""
    assignments: List[SectionFieldAssignmentCreate]


class BulkAssignmentResponse(BaseModel):
    """Response schema for bulk assignment creation"""
    created_count: int
    assignments: List[SectionFieldAssignmentRead]
