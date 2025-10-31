"""Database Connection schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class DatabaseConnectionCreate(BaseModel):
    """Schema for creating database connection"""
    handle: str = Field(..., max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    label: str = Field(..., max_length=200)
    description: Optional[str] = None
    database_type: str = Field(..., max_length=50)  # postgresql, mysql, sqlite

    # Connection details
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = None
    database_name: str = Field(..., max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = None  # Will be encrypted

    # For SQLite
    file_path: Optional[str] = Field(None, max_length=500)

    # Additional options
    connection_options: dict = Field(default_factory=dict)
    use_ssl: bool = False
    ssl_options: Optional[dict] = None

    project_id: UUID


class DatabaseConnectionUpdate(BaseModel):
    """Schema for updating database connection"""
    label: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = None
    database_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = None
    file_path: Optional[str] = Field(None, max_length=500)
    connection_options: Optional[dict] = None
    use_ssl: Optional[bool] = None
    ssl_options: Optional[dict] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class DatabaseConnectionRead(BaseModel):
    """Schema for reading database connection (password redacted)"""
    id: UUID
    handle: str
    label: str
    description: Optional[str]
    database_type: str
    host: Optional[str]
    port: Optional[int]
    database_name: str
    username: Optional[str]
    # password NOT included for security
    file_path: Optional[str]
    connection_options: dict
    use_ssl: bool
    ssl_options: Optional[dict]
    is_active: bool
    last_tested_at: Optional[datetime]
    test_status: Optional[str]
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatabaseConnectionTest(BaseModel):
    """Schema for testing database connection"""
    success: bool
    message: str
    latency_ms: Optional[float] = None
