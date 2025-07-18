from pydantic import BaseModel


class AvatarRequest(BaseModel):
    name: str | None = None
    instructions: str | None = None