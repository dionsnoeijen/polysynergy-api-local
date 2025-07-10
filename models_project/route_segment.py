import uuid

from sqlalchemy import (String, ForeignKey, Integer)
from enum import Enum
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models_project.base import ProjectBase


class RouteSegmentType(str, Enum):
    STATIC = "static"
    VARIABLE = "variable"

class VariableType(str, Enum):
    STRING = "string"
    NUMBER = "number"

class RouteSegment(ProjectBase):
    __tablename__ = "route_segments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), nullable=True)
    segment_order: Mapped[int] = mapped_column(Integer)
    type: Mapped[RouteSegmentType] = mapped_column(SQLEnum(*RouteSegmentType), default=RouteSegmentType.STATIC)
    name: Mapped[str] = mapped_column(String(50))
    default_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variable_type: Mapped[VariableType | None] = mapped_column(SQLEnum(*VariableType), nullable=True)

    route: Mapped["Route"] = relationship("Route", back_populates="segments")

    def __repr__(self):
        return f"<RouteSegment(name={self.name}, type={self.type})>"