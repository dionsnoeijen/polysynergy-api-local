import uuid

from sqlalchemy import ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class ChatWindowAccess(Base):
    __tablename__ = "chat_window_access"
    __table_args__ = (
        UniqueConstraint("account_id", "chat_window_id", name="uix_account_chat_window"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    chat_window_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_windows.id", ondelete="CASCADE"))

    can_view_flow: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view_output: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_response_transparency: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="chat_window_accesses")
    chat_window: Mapped["ChatWindow"] = relationship("ChatWindow", back_populates="accesses")
