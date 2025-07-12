from sqlalchemy import Column, String, UUID

from sqlalchemy.orm import relationship

from .base import Base

class NodeSetup(Base):
    __tablename__ = "node_setups"

    content_type = Column(String(100), nullable=False)
    object_id = Column(UUID, nullable=False)

    versions = relationship("NodeSetupVersion", back_populates="node_setup", cascade="all, delete-orphan")

    def resolve_parent(self, db):
        from models.route import Route
        from models.blueprint import Blueprint
        from models.service import Service
        from models.schedule import Schedule
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
