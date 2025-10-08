from pydantic import BaseModel
from uuid import UUID


class ProjectSimpleOut(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class TenantSimpleOut(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ChatWindowSimpleOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class PermissionsOut(BaseModel):
    can_view_flow: bool
    can_view_output: bool
    show_response_transparency: bool


class MyChatWindowOut(BaseModel):
    chat_window: ChatWindowSimpleOut
    project: ProjectSimpleOut
    tenant: TenantSimpleOut
    permissions: PermissionsOut

    model_config = {"from_attributes": True}
