from pydantic import BaseModel


class NodeSetupVersionOut(BaseModel):
    id: str
    version_number: int
    content: dict
    draft: bool
    published: bool