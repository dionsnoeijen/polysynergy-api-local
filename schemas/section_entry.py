"""Section Entry schemas - for data in section tables"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class SectionEntryCreate(BaseModel):
    """Schema for creating entry in section table"""
    field_data: dict[str, Any] = Field(..., description="Field handle → value mapping")


class SectionEntryUpdate(BaseModel):
    """Schema for updating entry in section table"""
    field_data: dict[str, Any] = Field(..., description="Field handle → value mapping to update")


class SectionEntryRead(BaseModel):
    """Schema for reading entry from section table"""
    id: UUID
    field_data: dict[str, Any]  # All field values
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionEntryQuery(BaseModel):
    """Schema for querying entries"""
    filters: Optional[dict[str, Any]] = Field(None, description="Field handle → value filters")
    order_by: Optional[str] = Field(None, description="Field handle to order by")
    order_direction: str = Field(default="asc", pattern=r'^(asc|desc)$')
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SectionEntryQueryResult(BaseModel):
    """Result of entry query"""
    entries: list[SectionEntryRead]
    total_count: int
    limit: int
    offset: int
