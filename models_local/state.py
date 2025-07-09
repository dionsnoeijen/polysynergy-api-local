from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime, timezone

from .base import LocalBase

class State(LocalBase):
    __tablename__ = "state"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<State(key={self.key})>"