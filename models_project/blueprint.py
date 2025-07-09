import uuid
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from .base import ProjectBase

class Blueprint(ProjectBase):
    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    node_setup = relationship(
        "NodeSetup",
        primaryjoin="and_(foreign(NodeSetup.object_id) == Blueprint.id, NodeSetup.content_type == 'blueprint')",
        uselist=False
    )

    def __repr__(self):
        return f"<Blueprint(name={self.name})>"