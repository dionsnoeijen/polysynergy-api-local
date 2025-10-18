from pydantic import BaseModel
from typing import Any
from datetime import datetime
from uuid import UUID

from .node_setup import NodeSetupOut

class ServiceMetadata(BaseModel):
    icon: str | None = ""
    category: str | None = ""
    description: str | None = ""

class ServiceOut(BaseModel):
    id: UUID
    name: str
    meta: ServiceMetadata
    created_at: datetime
    updated_at: datetime
    node_setup: NodeSetupOut | None = None
    project_ids: list[UUID] | None = None
    tenant_id: UUID | None = None

    model_config = { "populate_by_name": True }

class ServiceCreateIn(BaseModel):
    name: str
    meta: ServiceMetadata
    node_setup_content: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}

class ServiceShareIn(BaseModel):
    project_ids: list[UUID] | None = None
    tenant_wide: bool = False
    make_global: bool = False

    model_config = { "populate_by_name": True }

class ServiceShareOut(BaseModel):
    id: UUID
    name: str
    project_ids: list[UUID]
    tenant_id: UUID | None
    is_global: bool
    is_tenant_wide: bool

    model_config = { "populate_by_name": True }