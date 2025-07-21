import uuid

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class NodeSetupVersion(Base):
    __tablename__ = "node_setup_versions"

    node_setup_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("node_setups.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(JSON)
    executable: Mapped[str] = mapped_column(Text, default="")
    executable_hash: Mapped[str] = mapped_column(Text, default="")
    draft: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lambda_arn: Mapped[str | None] = mapped_column(Text, nullable=True)

    node_setup = relationship("NodeSetup", back_populates="versions")
    stage_links = relationship("NodeSetupVersionStage", back_populates="version", cascade="all, delete")

    def __repr__(self):
        return f"<NodeSetupVersion v{self.version_number}>"