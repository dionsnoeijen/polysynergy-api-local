from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NodeSetupVersionStageOut(BaseModel):
    version_id: UUID
    stage_id: UUID
    node_setup_id: UUID
    executable_hash: str | None = None
    published_at: datetime

    model_config = {"from_attributes": True}