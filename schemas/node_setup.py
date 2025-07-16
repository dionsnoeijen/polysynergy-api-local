from uuid import UUID

from pydantic import BaseModel

from schemas.node_setup_version import NodeSetupVersionOut


class NodeSetupOut(BaseModel):
    id: UUID
    versions: list[NodeSetupVersionOut]