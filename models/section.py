"""Section model - represents a content section (form/table)"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base

if TYPE_CHECKING:
    from models.section_field_assignment import SectionFieldAssignment
    from models.section_migration import SectionMigration
    from models.database_connection import DatabaseConnection
    from models.project import Project


class Section(Base):
    """
    Section represents a content type that maps to a database table.

    Each section:
    - Has assigned fields (via SectionFieldAssignment many-to-many)
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

    # Grid layout configuration (12-column grid with tabs, rows, cells)
    layout_config: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # Vectorization configuration (pgvector + Agno integration)
    vectorization_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "enabled": true,
    #   "provider": "openai",
    #   "api_key_secret_id": "uuid",
    #   "model": "text-embedding-3-small",
    #   "dimensions": 1536,
    #   "source_fields": ["title", "description"],
    #   "metadata_fields": ["id", "title", "status"],
    #   "search_type": "hybrid",
    #   "distance": "cosine"
    # }

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    migration_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False
    )  # pending, migrated, failed

    # Schema fingerprint - MD5 hash of field structure
    schema_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

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

    field_assignments: Mapped[list["SectionFieldAssignment"]] = relationship(
        "SectionFieldAssignment",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SectionFieldAssignment.sort_order"
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

    __table_args__ = (
        # Unique constraint: project_id + handle
        # Can't have two sections with same handle in one project
        UniqueConstraint('project_id', 'handle', name='uq_section_handle_per_project'),
    )

    def __repr__(self):
        return f"<Section(handle='{self.handle}', label='{self.label}', status='{self.migration_status}')>"
