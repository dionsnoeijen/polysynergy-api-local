import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from models import Project
from models.node_setup import NodeSetup
from models.node_setup_version import NodeSetupVersion
from schemas.node_setup_version import NodeSetupVersionUpdate, NodeSetupVersionOut
from services.codegen.build_executable import generate_code_from_json
from services.mock_sync_service import MockSyncService, get_mock_sync_service
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.put("/{type}/{setup_id}/version/{version_id}/", response_model=NodeSetupVersionOut)
def update_node_setup_version(
    type: str,
    setup_id: str,
    version_id: str,
    data: NodeSetupVersionUpdate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_or_403),
    mock_sync_service: MockSyncService = Depends(get_mock_sync_service)
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

    try:
        version.content = data.content
        version.executable = generate_code_from_json(data.content, version.id)
        db.commit()
        db.refresh(version)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=200, detail={"message": "Did not update version", "details": str(e)})

    try:
        mock_sync_service.sync_if_needed(version, project)
    except Exception as e:
        print("MockSyncService failed:")
        traceback.print_exc()

    return version