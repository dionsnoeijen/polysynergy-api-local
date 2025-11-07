"""Section Field Assignment - Many-to-many relationship between Section and Field"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base

if TYPE_CHECKING:
    from models.section import Section
    from models.field import Field


class SectionFieldAssignment(Base):
    """
    Assignment of a Field to a Section with layout-specific configuration.

    This model represents the many-to-many relationship between Sections and Fields.
    Layout and presentation settings are stored here, while the field definition
    itself is stored in the Field model.
    """
    __tablename__ = "section_field_assignments"

    # Relationships
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Layout/UI Configuration (specific to this assignment)
    # Note: Form layout (width, position) is now stored in Section.layout_config
    tab_name: Mapped[str] = mapped_column(String(100), default="Content", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Field can be required in one section but not in another
    is_required_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    section: Mapped["Section"] = relationship(
        "Section",
        back_populates="field_assignments"
    )

    field: Mapped["Field"] = relationship(
        "Field",
        backref="section_assignments"
    )

    __table_args__ = (
        # A field can only be assigned once to a section
        UniqueConstraint('section_id', 'field_id', name='uq_section_field_assignment'),
    )

    # Property accessors for field details (for Pydantic serialization)
    @property
    def field_handle(self) -> str:
        return self.field.handle if self.field else ""

    @property
    def field_label(self) -> str:
        return self.field.label if self.field else ""

    @property
    def field_type_handle(self) -> str:
        return self.field.field_type_handle if self.field else ""

    @property
    def field_settings(self) -> dict:
        return self.field.field_settings if self.field else {}

    @property
    def default_value(self) -> str | None:
        return self.field.default_value if self.field else None

    @property
    def help_text(self) -> str | None:
        return self.field.help_text if self.field else None

    @property
    def placeholder(self) -> str | None:
        return self.field.placeholder if self.field else None

    @property
    def is_required(self) -> bool:
        return self.field.is_required if self.field else False

    @property
    def is_unique(self) -> bool:
        return self.field.is_unique if self.field else False

    @property
    def custom_validation_rules(self) -> dict | None:
        return self.field.custom_validation_rules if self.field else None

    @property
    def related_section_id(self) -> uuid.UUID | None:
        return self.field.related_section_id if self.field else None

    def __repr__(self):
        return f"<SectionFieldAssignment(section_id='{self.section_id}', field_id='{self.field_id}', order={self.sort_order})>"
