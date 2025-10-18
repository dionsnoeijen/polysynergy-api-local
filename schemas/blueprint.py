from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from datetime import datetime

from schemas.node_setup import NodeSetupOut


class BlueprintMetadata(BaseModel):
    icon: str | None = ""
    category: str | None = ""
    description: str | None = ""

class BlueprintIn(BaseModel):
    name: str
    meta: BlueprintMetadata
    node_setup: dict[str, Any] | None = None

    model_config = { "populate_by_name": True }

class BlueprintOut(BaseModel):
    id: UUID
    name: str
    meta: BlueprintMetadata
    created_at: datetime
    updated_at: datetime
    node_setup: NodeSetupOut | None = None
    project_ids: list[UUID] | None = None
    tenant_id: UUID | None = None

    model_config = { "populate_by_name": True }

class BlueprintShareIn(BaseModel):
    project_ids: list[UUID] | None = None
    tenant_wide: bool = False
    make_global: bool = False

    model_config = { "populate_by_name": True }

class BlueprintShareOut(BaseModel):
    id: UUID
    name: str
    project_ids: list[UUID]
    tenant_id: UUID | None
    is_global: bool
    is_tenant_wide: bool

    model_config = { "populate_by_name": True }