from typing import List
from sqlalchemy import String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base


class AccountRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    CHAT_USER = "chat_user"


class Account(Base):
    __tablename__ = "accounts"

    cognito_id: Mapped[str] = mapped_column(String(255), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[AccountRole] = mapped_column(SQLEnum(AccountRole, values_callable=lambda x: [e.value for e in x]), default=AccountRole.CHAT_USER, nullable=False)

    single_user: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False)

    memberships: Mapped[List["Membership"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    chat_window_accesses: Mapped[List["ChatWindowAccess"]] = relationship(back_populates="account", cascade="all, delete-orphan")