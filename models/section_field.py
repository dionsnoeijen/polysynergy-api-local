"""Section Field model - field configuration within a section"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base

if TYPE_CHECKING:
    from models.section import Section


class SectionField(Base):
    """
    SectionField defines a field within a section.

    Combines:
    - Field type (from field_type_registry)
    - Field-specific settings
    - Validation rules
    - UI layout configuration
    """
    __tablename__ = "section_fields"

    # Section relationship
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Field definition
    handle: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)

    # Field type reference
    field_type_handle: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("field_type_registry.handle", ondelete="RESTRICT"),
        nullable=False
    )

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

    # UI/Layout
    ui_width: Mapped[str] = mapped_column(
        String(20),
        default="full",
        nullable=False
    )  # full, half, third, quarter
    tab_name: Mapped[str] = mapped_column(String(100), default="Content", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relations (for relation field type)
    related_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    section: Mapped["Section"] = relationship("Section", back_populates="fields")

    field_type: Mapped["FieldTypeRegistry"] = relationship("FieldTypeRegistry")

    related_section: Mapped[Optional["Section"]] = relationship(
        "Section",
        foreign_keys=[related_section_id],
        remote_side="Section.id"
    )

    def __repr__(self):
        return f"<SectionField(handle='{self.handle}', label='{self.label}', type='{self.field_type_handle}')>"

    __table_args__ = (
        # Unique constraint: section_id + handle
        # Can't have two fields with same handle in one section
        dict(
            name="uq_section_field_handle",
            sqlite_on_conflict="IGNORE",
            postgresql_on_conflict="DO NOTHING",
        ),
    )
