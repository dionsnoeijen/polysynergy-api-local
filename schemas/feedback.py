from pydantic import BaseModel, EmailStr
from datetime import datetime


class FeedbackCreate(BaseModel):
    email: EmailStr
    message: str
    timestamp: datetime
    user_agent: str | None = None


class FeedbackResponse(BaseModel):
    success: bool
    message: str
