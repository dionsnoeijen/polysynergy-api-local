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

    model_config = { "populate_by_name": True }

class ServiceCreateIn(BaseModel):
    name: str
    meta: ServiceMetadata
    node_setup_content: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}