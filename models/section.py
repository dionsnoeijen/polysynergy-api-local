"""Section model - represents a content section (form/table)"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base

if TYPE_CHECKING:
    from models.section_field import SectionField
    from models.section_migration import SectionMigration
    from models.database_connection import DatabaseConnection
    from models.project import Project


class Section(Base):
    """
    Section represents a content type that maps to a database table.

    Each section:
    - Defines fields (via SectionField)
    - Creates a table in a database (custom schema or external DB)
    - Has migration history
    - Belongs to a project
    - Can use PolySynergy DB or external database connection
    """
    __tablename__ = "sections"

    # Basic info
    handle: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Table information
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    title_field_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    migration_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False
    )  # pending, migrated, failed

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Database connection (NULL = use PolySynergy database)
    database_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("database_connections.id", ondelete="SET NULL"),
        nullable=True
    )

    # Reference to last applied migration
    last_migration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("section_migrations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")

    database_connection: Mapped[Optional["DatabaseConnection"]] = relationship(
        "DatabaseConnection",
        back_populates="sections"
    )

    fields: Mapped[list["SectionField"]] = relationship(
        "SectionField",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SectionField.sort_order"
    )

    migrations: Mapped[list["SectionMigration"]] = relationship(
        "SectionMigration",
        back_populates="section",
        cascade="all, delete-orphan",
        foreign_keys="SectionMigration.section_id",
        order_by="SectionMigration.created_at.desc()"
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"<Section(handle='{self.handle}', label='{self.label}', status='{self.migration_status}')>"
