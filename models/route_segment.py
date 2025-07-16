import uuid

from sqlalchemy import (String, ForeignKey, Integer)
from enum import Enum
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from sqlalchemy.dialects.postgresql import UUID


class RouteSegmentType(str, Enum):
    STATIC = "static"
    VARIABLE = "variable"

class VariableType(str, Enum):
    STRING = "string"
    NUMBER = "number"

class RouteSegment(Base):
    __tablename__ = "route_segments"

    route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True)
    segment_order: Mapped[int] = mapped_column(Integer)
    type: Mapped[RouteSegmentType] = mapped_column(
        SQLEnum(RouteSegmentType),
        name="route_segment_type_enum"
    )
    name: Mapped[str] = mapped_column(String(50))
    default_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variable_type: Mapped[VariableType | None] = mapped_column(
        SQLEnum(VariableType),
        nullable=True,
        name="variable_type_enum"
    )

    route: Mapped["Route"] = relationship("Route", back_populates="segments")

    def __repr__(self):
        return f"<RouteSegment(name={self.name}, type={self.type})>"

    def __str__(self):
        return f"{self.name}"