from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.project_session import get_active_project_db
from models_project.node_setup import NodeSetup
from models_project.node_setup_version import NodeSetupVersion
from schemas.node_setup_version import NodeSetupVersionUpdate, NodeSetupVersionOut
from services.codegen.build_executable import generate_code_from_json

# from services.mock_sync import MockSyncService

router = APIRouter()

@router.put("/{type}/{setup_id}/version/{version_id}/", response_model=NodeSetupVersionOut)
def update_node_setup_version(
    type: str,
    setup_id: str,
    version_id: str,
    data: NodeSetupVersionUpdate,
    db: Session = Depends(get_active_project_db)
):
    node_setup = db.query(NodeSetup).filter_by(content_type=type, object_id=setup_id).first()
    if not node_setup:
        raise HTTPException(status_code=404, detail="NodeSetup not found")

    version = db.query(NodeSetupVersion).filter_by(id=version_id, node_setup_id=node_setup.id).first()
    if not version:
        raise HTTPException(status_code=404, detail="NodeSetupVersion not found")

    if not version.draft:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "This version is not editable.",
                "message": "Do you want to create a new version based on this one?",
                "requires_duplication": True,
                "version_id": version.id
            }
        )

    version.content = data.content
    version.executable = generate_code_from_json(data.content, version.id)
    db.commit()
    db.refresh(version)

    # Mock sync (eventueel in background task)
    # try:
    #     MockSyncService.sync_if_needed(version)
    # except Exception as e:
    #     print(f"MockSyncService failed: {e}")

    return version