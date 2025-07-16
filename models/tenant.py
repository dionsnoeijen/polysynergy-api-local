from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(unique=True)
    memberships: Mapped[list["Membership"]] = relationship("Membership", back_populates="tenant")
    projects: Mapped[list["Project"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    services: Mapped[list["Service"]] = relationship("Service", back_populates="tenant")
    blueprints: Mapped[list["Blueprint"]] = relationship("Blueprint", back_populates="tenant")