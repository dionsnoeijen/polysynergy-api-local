"""Section schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class SectionCreate(BaseModel):
    """Schema for creating section"""
    handle: str = Field(..., max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    label: str = Field(..., max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)

    # Table configuration
    table_name: str = Field(..., max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    title_field_handle: Optional[str] = Field(None, max_length=100)

    # Project and database
    project_id: UUID
    database_connection_id: Optional[UUID] = None  # NULL = PolySynergy DB


class SectionUpdate(BaseModel):
    """Schema for updating section"""
    label: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    title_field_handle: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class SectionRead(BaseModel):
    """Schema for reading section"""
    id: UUID
    handle: str
    label: str
    description: Optional[str]
    icon: Optional[str]
    table_name: str
    title_field_handle: Optional[str]
    is_active: bool
    migration_status: str  # pending, migrated, failed
    project_id: UUID
    database_connection_id: Optional[UUID]
    last_migration_id: Optional[UUID]
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionWithFields(SectionRead):
    """Section with its fields included"""
    fields: list["SectionFieldRead"] = []

    model_config = {"from_attributes": True}


# Import after class definition to avoid circular import
from schemas.section_field import SectionFieldRead
SectionWithFields.model_rebuild()
