"""Section Migration model - tracks database migrations for sections"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base

if TYPE_CHECKING:
    from models.section import Section


class SectionMigration(Base):
    """
    SectionMigration tracks generated and applied database migrations.

    Each migration:
    - Has SQL to execute
    - Tracks status (generated, applied, failed)
    - Records who applied it and when
    - Has a version number
    """
    __tablename__ = "section_migrations"

    # Section relationship
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Migration details
    migration_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # create_table, add_field, modify_field, drop_field, drop_table

    migration_sql: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        default="generated",
        nullable=False
    )  # generated, applied, failed, rolled_back

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    generated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    applied_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow())
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Version tracking
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    section: Mapped["Section"] = relationship(
        "Section",
        back_populates="migrations",
        foreign_keys=[section_id]
    )

    def __repr__(self):
        return f"<SectionMigration(type='{self.migration_type}', status='{self.status}', version={self.version})>"
