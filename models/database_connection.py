"""Database Connection model - defines where section data is stored"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base

if TYPE_CHECKING:
    from models.section import Section
    from models.project import Project


class DatabaseConnection(Base):
    """
    DatabaseConnection defines where section tables are created and data is stored.

    Supports:
    - PostgreSQL (default and PolySynergy database)
    - MySQL
    - SQLite
    - Other SQLAlchemy-supported databases

    If no connection is specified for a section, the PolySynergy database is used.
    """
    __tablename__ = "database_connections"

    # Basic info
    handle: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Database type
    database_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # postgresql, mysql, sqlite, etc.

    # Connection details (encrypted in production)
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Should be encrypted!

    # Additional connection options (JSON)
    connection_options: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # For SQLite
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # SSL/TLS
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ssl_options: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    test_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )  # success, failed, pending

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")

    sections: Mapped[list["Section"]] = relationship(
        "Section",
        back_populates="database_connection"
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"<DatabaseConnection(handle='{self.handle}', type='{self.database_type}', db='{self.database_name}')>"

    def get_connection_string(self) -> str:
        """Generate SQLAlchemy connection string"""
        if self.database_type == "sqlite":
            return f"sqlite:///{self.file_path}"

        # PostgreSQL, MySQL, etc.
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        port = f":{self.port}" if self.port else ""
        return f"{self.database_type}://{auth}{self.host}{port}/{self.database_name}"
