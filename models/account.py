from typing import List, Optional
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

    # Authentication fields (generic for both SAAS and standalone modes)
    external_user_id: Mapped[str] = mapped_column(String(255), unique=True)  # Was: cognito_id
    auth_provider: Mapped[str] = mapped_column(String(50), default="cognito")  # "cognito" or "standalone"

    # Standalone auth fields (only used when auth_provider="standalone")
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # 2FA/TOTP fields
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # User profile fields
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[AccountRole] = mapped_column(SQLEnum(AccountRole, values_callable=lambda x: [e.value for e in x]), default=AccountRole.CHAT_USER, nullable=False)

    single_user: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False)

    memberships: Mapped[List["Membership"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    chat_window_accesses: Mapped[List["ChatWindowAccess"]] = relationship(back_populates="account", cascade="all, delete-orphan")