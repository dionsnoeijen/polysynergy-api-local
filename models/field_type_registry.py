"""Field Type Registry model - stores registered field types from section_field package"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class FieldTypeRegistry(Base):
    """
    Registry of available field types from polysynergy_section_field package.
    Auto-populated on startup by scanning registered field types.
    """
    __tablename__ = "field_type_registry"

    handle: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    postgres_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ui_component: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # JSON schema for field-specific settings
    settings_schema: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Version tracking
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamp when this field type was registered
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow())

    def __repr__(self):
        return f"<FieldTypeRegistry(handle='{self.handle}', label='{self.label}')>"
