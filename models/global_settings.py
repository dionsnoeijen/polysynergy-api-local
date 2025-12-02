"""
Global settings model for application-wide configuration.
Singleton pattern - only one row exists with id=1.
"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from .base import Base


class GlobalSettings(Base):
    """
    Global application settings (singleton).

    This table contains system-wide configuration that applies to all users/tenants.
    Only one row should exist (id=1).
    """
    __tablename__ = "global_settings"

    # Branding
    logo_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="URL to custom logo (stored in MinIO). Falls back to default if null."
    )

    accent_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#0ea5e9",
        comment="Primary accent color in hex format (e.g., #0ea5e9 for sky-blue)"
    )

    def __repr__(self):
        return f"<GlobalSettings(logo_url={self.logo_url}, accent_color={self.accent_color})>"
