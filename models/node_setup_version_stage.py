import uuid
from datetime import datetime, timezone

from sqlalchemy import Text, ForeignKey
from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class NodeSetupVersionStage(Base):
    __tablename__ = "node_setup_version_stages"
    __table_args__ = (
        UniqueConstraint("stage_id", "node_setup_id", name="uq_stage_node_setup"),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("node_setup_versions.id"), primary_key=True)
    stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stages.id"), primary_key=True)
    node_setup_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("node_setups.id"), nullable=False)

    executable_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    version = relationship("NodeSetupVersion", back_populates="stage_links")
    stage = relationship("Stage", back_populates="version_links")
    node_setup = relationship("NodeSetup")

    def __repr__(self):
        return f"<StageLink stage={self.stage_id} → version={self.version_id}>"