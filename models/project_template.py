import uuid
from sqlalchemy import ForeignKey, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class ProjectTemplate(Base):
    """
    Stores Jinja base templates at project level.

    Templates can be used with {% extends "template_name" %} in Layout nodes.
    Each project can have multiple templates with unique names.
    """
    __tablename__ = "project_templates"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    project: Mapped["Project"] = relationship(back_populates="templates")
