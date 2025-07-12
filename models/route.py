import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, Boolean, Text, Enum, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum

from .base import Base
from .route_segment import RouteSegment


class Method(PyEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class Route(Base):
    __tablename__ = "routes"

    description: Mapped[str] = mapped_column(Text, nullable=True)
    require_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    method: Mapped[Method] = mapped_column(
        Enum(Method, name="http_method_enum"), default=Method.GET
    )

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["Project"] = relationship("Project", back_populates="routes")
    segments: Mapped[list["RouteSegment"]] = relationship("RouteSegment", back_populates="route", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Route(id={self.id}, method={self.method})>"