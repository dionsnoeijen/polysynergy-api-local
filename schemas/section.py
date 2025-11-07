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

    # Grid layout configuration (optional at creation)
    layout_config: Optional[dict] = Field(default_factory=lambda: {"tabs": {"Content": {"rows": []}}})

    # Project and database
    project_id: UUID
    database_connection_id: Optional[UUID] = None  # NULL = PolySynergy DB


class SectionUpdate(BaseModel):
    """Schema for updating section"""
    label: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    title_field_handle: Optional[str] = Field(None, max_length=100)
    layout_config: Optional[dict] = None
    vectorization_config: Optional[dict] = None
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
    layout_config: dict
    vectorization_config: Optional[dict]
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
    """Section with its field assignments included"""
    field_assignments: list["SectionFieldAssignmentWithFieldRead"] = []

    model_config = {"from_attributes": True}


class SectionExportRequest(BaseModel):
    """Schema for requesting CSV export of section data"""
    field_handles: list[str] = Field(..., min_length=1, description="List of field handles to include in export")
    limit: int = Field(10000, ge=1, le=100000, description="Maximum number of records to export")
    offset: int = Field(0, ge=0, description="Number of records to skip")
    search: Optional[str] = Field(None, description="Optional search term to filter records")


# Import after class definition to avoid circular import
from schemas.section_field_assignment import SectionFieldAssignmentWithFieldRead
SectionWithFields.model_rebuild()
