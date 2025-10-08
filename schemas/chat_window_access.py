from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ChatWindowAccessBase(BaseModel):
    can_view_flow: bool = False
    can_view_output: bool = False
    show_response_transparency: bool = True


class ChatWindowAccessCreateIn(ChatWindowAccessBase):
    account_id: UUID


class ChatWindowAccessUpdateIn(BaseModel):
    can_view_flow: bool | None = None
    can_view_output: bool | None = None
    show_response_transparency: bool | None = None


class AccountSimpleOut(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str

    model_config = {"from_attributes": True}


class ChatWindowAccessOut(ChatWindowAccessBase):
    id: UUID
    account_id: UUID
    chat_window_id: UUID
    account: AccountSimpleOut
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
