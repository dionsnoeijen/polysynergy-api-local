import uuid

from sqlalchemy import String, Boolean, Integer, UniqueConstraint, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class Stage(Base):
    __tablename__ = "stages"
    __table_args__ = (
        UniqueConstraint("name", name="uq_stage_name"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project: Mapped["Project"] = relationship("Project", back_populates="stages")

    version_links = relationship("NodeSetupVersionStage", back_populates="stage", cascade="all, delete")

    def __repr__(self):
        return f"<Stage name={self.name}>"