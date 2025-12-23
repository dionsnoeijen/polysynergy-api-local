from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class EmbedTokenBase(BaseModel):
    sessions_enabled: bool = True
    sidebar_visible: bool = True


class EmbedTokenCreateIn(EmbedTokenBase):
    chat_window_id: UUID


class EmbedTokenUpdateIn(BaseModel):
    sessions_enabled: bool | None = None
    sidebar_visible: bool | None = None
    is_active: bool | None = None


class EmbedTokenOut(EmbedTokenBase):
    id: UUID
    token: str
    chat_window_id: UUID
    project_id: UUID
    is_active: bool
    last_used_at: datetime | None = None
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmbedTokenListOut(BaseModel):
    id: UUID
    token: str
    chat_window_id: UUID
    is_active: bool
    sessions_enabled: bool
    sidebar_visible: bool
    usage_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# Schema for embedded chat config (public API)
class EmbeddedChatConfigOut(BaseModel):
    chat_window_id: UUID
    chat_window_name: str
    sessions_enabled: bool
    sidebar_visible: bool


# Schema for embedded execution request
class EmbeddedExecuteIn(BaseModel):
    message: str
    session_id: UUID | None = None
    prompt_node_id: UUID | None = None  # Which prompt node to target (for multi-prompt flows)


# Schema for embedded HITL resume
class EmbeddedResumeIn(BaseModel):
    session_id: UUID
    execution_id: UUID
    response: str


# Schema for session list
class EmbeddedSessionOut(BaseModel):
    id: UUID
    created_at: datetime
    last_message_at: datetime | None = None
    message_count: int = 0


# Schema for embedded prompt node info
class EmbeddedPromptOut(BaseModel):
    id: UUID
    name: str
    handle: str


# Schema for embedded prompts list
class EmbeddedPromptsOut(BaseModel):
    prompts: list[EmbeddedPromptOut]
