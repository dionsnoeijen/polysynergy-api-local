from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from schemas.node_setup import NodeSetupOut


class BlueprintMetadata(BaseModel):
    icon: Optional[str] = ""
    category: Optional[str] = ""
    description: Optional[str] = ""

class BlueprintIn(BaseModel):
    name: str
    meta: BlueprintMetadata = Field(alias="metadata")
    node_setup: Optional[Dict[str, Any]] = None  # ← als input mag dit vrij blijven

    class Config:
        validate_by_name = True  # ← deze regel is nodig

class BlueprintOut(BaseModel):
    id: str
    name: str
    metadata: BlueprintMetadata = Field(alias="meta")
    created_at: datetime
    updated_at: datetime
    node_setup: Optional[NodeSetupOut] = None

    class Config:
        populate_by_name = True