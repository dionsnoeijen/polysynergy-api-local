from pydantic import BaseModel

from schemas.node_setup_version import NodeSetupVersionOut


class NodeSetupOut(BaseModel):
    id: str
    versions: list[NodeSetupVersionOut]