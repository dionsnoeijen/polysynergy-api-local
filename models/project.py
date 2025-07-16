import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class Project(Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))

    rest_api_gateway_id: Mapped[Optional[str]] = mapped_column(nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="projects")

    blueprints: Mapped[list["Blueprint"]] = relationship(
        "Blueprint",
        secondary="blueprint_project_link",
        back_populates="projects"
    )

    services: Mapped[list["Service"]] = relationship(
        "Service",
        secondary="service_project_link",
        back_populates="projects",
    )

    routes: Mapped[list["Route"]] = relationship("Route", back_populates="project", cascade="all, delete-orphan")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="project", cascade="all, delete-orphan")
    stages: Mapped[list["Stage"]] = relationship("Stage", back_populates="project", cascade="all, delete-orphan")

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
