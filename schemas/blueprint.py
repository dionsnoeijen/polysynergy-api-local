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

    model_config = { "populate_by_name": True }