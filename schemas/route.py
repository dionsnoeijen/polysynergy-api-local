from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime

from models.route_segment import RouteSegmentType, VariableType
from schemas.node_setup import NodeSetupOut
from schemas.node_setup_version import NodeSetupVersionSimpleOut, NodeSetupVersionOut


# --- SEGMENTS ---

class RouteSegmentIn(BaseModel):
    segment_order: int
    type: RouteSegmentType
    name: str
    default_value: Optional[str] = None
    variable_type: VariableType | None = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        return v.lower() if isinstance(v, str) else v

    @field_validator("variable_type", mode="before")
    @classmethod
    def validate_variable_type(cls, v):
        return v.lower() if isinstance(v, str) else v


class RouteSegmentOut(RouteSegmentIn):
    id: UUID

    @field_validator("type", mode="before")
    @classmethod
    def serialize_type(cls, v):
        return v.lower() if isinstance(v, str) else v

    model_config = {"from_attributes": True}


# --- DYNAMIC ROUTES ---

class RouteCreateIn(BaseModel):
    description: str
    method: str
    segments: list[RouteSegmentIn]


class RouteListOut(BaseModel):
    id: UUID
    description: str
    method: str
    created_at: datetime
    updated_at: datetime
    segments: list[RouteSegmentOut]
    versions: list[NodeSetupVersionSimpleOut] = []

    model_config = {"from_attributes": True}

class RouteDetailOut(BaseModel):
    id: UUID
    description: str
    method: str
    created_at: datetime
    updated_at: datetime
    segments: list[RouteSegmentOut]
    node_setup: NodeSetupOut | None = None

    model_config = {"from_attributes": True}

