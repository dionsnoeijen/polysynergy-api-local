"""Section Migration schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class SectionMigrationGenerate(BaseModel):
    """Schema for generating migration"""
    section_id: UUID
    description: Optional[str] = None


class SectionMigrationApply(BaseModel):
    """Schema for applying migration"""
    confirm: bool = Field(..., description="Must be True to apply migration")


class SectionMigrationRead(BaseModel):
    """Schema for reading migration"""
    id: UUID
    section_id: UUID
    migration_type: str  # create_table, add_field, modify_field, drop_field, drop_table
    migration_sql: str
    description: Optional[str]
    status: str  # generated, applied, failed, rolled_back
    error_message: Optional[str]
    generated_by: Optional[str]
    applied_by: Optional[str]
    generated_at: datetime
    applied_at: Optional[datetime]
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MigrationGenerateResponse(BaseModel):
    """Response for generated migration"""
    migration_id: UUID
    migration_sql: str
    description: str
    changes: list[dict]  # List of changes that will be applied
