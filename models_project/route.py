import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, Boolean, ForeignKey, Integer, Text, Enum
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

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    require_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    method: Mapped[Method] = mapped_column(Enum(Method), default=Method.GET)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    segments: Mapped[list["RouteSegment"]] = relationship("RouteSegment", back_populates="route", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Route(id={self.id}, method={self.method})>"