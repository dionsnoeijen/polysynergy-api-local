from uuid import UUID

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models import NodeSetupVersion


class NodeSetupRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_404(self, version_id: UUID) -> NodeSetupVersion:
        version = self.session.query(NodeSetupVersion).filter_by(id=version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="NodeSetupVersion not found")
        return version

def get_node_setup_repository(db: Session = Depends(get_db)) -> NodeSetupRepository:
    return NodeSetupRepository(db)