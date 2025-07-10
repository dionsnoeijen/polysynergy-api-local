from pydantic import BaseModel
from uuid import UUID


class StageBase(BaseModel):
    name: str
    is_production: bool = False

class ReorderStagesIn(BaseModel):
    stage_ids: list[str]

class StageUpdate(BaseModel):
    name: str | None = None
    is_production: bool | None = None

class StageCreate(BaseModel):
    name: str
    is_production: bool = False

class StageOut(StageBase):
    id: UUID
    name: str
    order: int

    model_config = {"from_attributes": True}
