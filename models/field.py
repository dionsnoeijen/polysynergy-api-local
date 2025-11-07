"""Field model - Reusable field library per project"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base

if TYPE_CHECKING:
    from models.section import Section
    from models.project import Project


class Field(Base):
    """
    Field represents a reusable field definition in the field library.

    Fields can be assigned to multiple sections.
    Layout-specific settings (sort_order, ui_width, tab_name) are stored
    in the SectionFieldAssignment model.
    """
    __tablename__ = "fields"

    # Project relationship - fields are scoped per project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Field definition
    handle: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)

    # Field type reference (runtime-loaded from section_field package)
    field_type_handle: Mapped[str] = mapped_column(String(100), nullable=False)

    # Field settings (specific to field type)
    field_settings: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # Default/placeholder values
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    help_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    placeholder: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Validation
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_unique: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    custom_validation_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relations (for relation field type)
    related_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")

    related_section: Mapped[Optional["Section"]] = relationship(
        "Section",
        foreign_keys=[related_section_id],
    )

    # Many-to-many relationship to sections via assignments
    # This will be set up in SectionFieldAssignment

    __table_args__ = (
        # Unique constraint: project_id + handle
        # Can't have two fields with same handle in one project
        UniqueConstraint('project_id', 'handle', name='uq_field_handle_per_project'),
    )

    def __repr__(self):
        return f"<Field(handle='{self.handle}', label='{self.label}', type='{self.field_type_handle}')>"
