from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime

from schemas.node_setup import NodeSetupOut


class BlueprintMetadata(BaseModel):
    icon: str | None = ""
    category: str | None = ""
    description: str | None = ""

class BlueprintIn(BaseModel):
    name: str
    meta: BlueprintMetadata = Field(alias="metadata")
    node_setup: dict[str, Any] | None = None

    model_config = { "populate_by_name": True }

class BlueprintOut(BaseModel):
    id: str
    name: str
    metadata: BlueprintMetadata = Field(alias="meta")
    created_at: datetime
    updated_at: datetime
    node_setup: NodeSetupOut | None = None

    model_config = { "populate_by_name": True }