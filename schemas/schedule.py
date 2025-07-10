from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from schemas.node_setup import NodeSetupOut
from schemas.node_setup_version import NodeSetupVersionSimpleOut


class ScheduleBase(BaseModel):
    name: str
    cron_expression: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool


class ScheduleListOut(ScheduleBase):
    id: UUID
    versions: list[NodeSetupVersionSimpleOut] = []

    model_config = {"from_attributes": True}

class ScheduleCreateIn(BaseModel):
    name: str = Field(..., max_length=255)
    cron_expression: str = Field(..., max_length=100)
    start_time: datetime | None = None
    end_time: datetime | None  = None
    is_active: bool = True

class ScheduleDetailOut(BaseModel):
    id: UUID
    name: str
    cron_expression: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool
    node_setup: NodeSetupOut | None = None

class ScheduleUpdateIn(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None