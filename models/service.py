import uuid

from sqlalchemy import String, JSON, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class Service(Base):
    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, nullable=True)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="services")

    projects: Mapped[list["Project"]] = relationship(
        "Project",
        secondary="service_project_link",
        back_populates="services",
    )

    def is_global(self) -> bool:
        return self.tenant_id is None and not self.projects

    def is_tenant_specific(self) -> bool:
        return self.tenant_id is not None and not self.projects

    def __repr__(self):
        return f"<Service(name={self.name})>"
