import uuid

from sqlalchemy import (
    Text, Enum, ForeignKey, UUID
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
    method: Mapped[Method] = mapped_column(
        Enum(Method, name="http_method_enum"), default=Method.GET
    )

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project: Mapped["Project"] = relationship("Project", back_populates="routes")
    segments: Mapped[list["RouteSegment"]] = relationship("RouteSegment", back_populates="route", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Route(id={self.id}, method={self.method})>"

    def get_segment_string(self):
        return "/".join(str(segment) for segment in self.segments)

    def __str__(self):
        return f"{self.project.name} - {self.get_segment_string()}"