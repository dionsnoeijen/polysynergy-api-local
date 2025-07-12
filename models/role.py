from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from .base import Base

class Role(Base):
    __tablename__ = "role"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
