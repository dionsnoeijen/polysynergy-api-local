from uuid import UUID

from pydantic import BaseModel
from typing import Any

class NodeSetupVersionOut(BaseModel):
    id: UUID
    version_number: int
    content: dict
    draft: bool
    published: bool

    model_config = {"from_attributes": True}

class NodeSetupVersionUpdate(BaseModel):
    content: dict[str, Any]

class NodeSetupVersionSimpleOut(BaseModel):
    id: UUID
    version_number: int
    published: bool
    draft: bool

    model_config = {"from_attributes": True}
