from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from schemas.node_setup import NodeSetupOut
from schemas.node_setup_version import NodeSetupVersionSimpleOut
from schemas.chat_window_access import ChatWindowAccessOut


class ChatWindowBase(BaseModel):
    name: str
    description: str | None = None


class ChatWindowListOut(ChatWindowBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    versions: list[NodeSetupVersionSimpleOut] = []

    model_config = {"from_attributes": True}


class ChatWindowCreateIn(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None


class ChatWindowDetailOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    node_setup: NodeSetupOut | None = None
    accesses: list[ChatWindowAccessOut] = []

    model_config = {"from_attributes": True}


class ChatWindowUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None


class ChatWindowPublishIn(BaseModel):
    pass  # No stage - always "mock" internally


class ChatWindowUnpublishIn(BaseModel):
    pass  # No stage - always "mock" internally
