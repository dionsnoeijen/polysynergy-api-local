from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(unique=True)
    projects: Mapped[list["Project"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    services: Mapped[list["Service"]] = relationship("Service", back_populates="tenant")