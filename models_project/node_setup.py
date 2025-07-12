from sqlalchemy import Column, String, DateTime
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import relationship

from .base import Base

class NodeSetup(Base):
    __tablename__ = "node_setups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_type = Column(String(100), nullable=False)  # e.g. 'blueprint', 'service', etc.
    object_id = Column(String, nullable=False)  # UUID as string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    versions = relationship("NodeSetupVersion", back_populates="node_setup", cascade="all, delete-orphan")

    # Relationship-like access via helper
    def resolve_parent(self, db):
        from models_project.route import Route
        from models_project.blueprint import Blueprint
        from models_project.service import Service
        from models_project.schedule import Schedule
        model_map = {
            "route": Route,
            "blueprint": Blueprint,
            "service": Service,
            "schedule": Schedule,
        }
        Model = model_map.get(self.content_type)
        if not Model:
            return None
        return db.query(Model).filter_by(id=self.object_id).first()

    def __repr__(self):
        return f"<NodeSetup(content_type={self.content_type}, object_id={self.object_id})>"
