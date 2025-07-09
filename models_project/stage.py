import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import ProjectBase  # local base class

class Stage(ProjectBase):
    __tablename__ = "stages"
    __table_args__ = (
        UniqueConstraint("name", name="uq_stage_name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Stage name={self.name}>"