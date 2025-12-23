import uuid
from sqlalchemy import String, Text, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ChatWindow(Base):
    __tablename__ = "chat_windows"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="chat_windows")
    accesses: Mapped[list["ChatWindowAccess"]] = relationship("ChatWindowAccess", back_populates="chat_window", cascade="all, delete-orphan")
    embed_tokens: Mapped[list["EmbedToken"]] = relationship("EmbedToken", back_populates="chat_window", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatWindow(name={self.name})>"
