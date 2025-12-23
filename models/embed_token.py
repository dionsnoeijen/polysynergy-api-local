import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def generate_embed_token() -> str:
    """Generate a secure embed token with 'emb_' prefix."""
    return f"emb_{secrets.token_urlsafe(32)}"


class EmbedToken(Base):
    __tablename__ = "embed_tokens"

    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=generate_embed_token)

    chat_window_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_windows.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Configuration
    sessions_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sidebar_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    chat_window: Mapped["ChatWindow"] = relationship("ChatWindow", back_populates="embed_tokens")
    project: Mapped["Project"] = relationship("Project", back_populates="embed_tokens")

    def __repr__(self):
        return f"<EmbedToken(id={self.id}, chat_window_id={self.chat_window_id}, active={self.is_active})>"
