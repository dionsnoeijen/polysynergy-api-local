import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Membership(Base):
    __tablename__ = "membership"
    __table_args__ = (
        UniqueConstraint("account_id", "tenant_id", name="uix_account_tenant"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("role.id", ondelete="SET NULL"), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="memberships")
    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    role: Mapped[Optional["Role"]] = relationship(back_populates="memberships")