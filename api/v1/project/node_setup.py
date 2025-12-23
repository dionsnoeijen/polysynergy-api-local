import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from models import Project
from models.node_setup import NodeSetup
from models.node_setup_version import NodeSetupVersion
from models.project_template import ProjectTemplate
from schemas.node_setup_version import NodeSetupVersionUpdate, NodeSetupVersionOut
from services.mock_sync_service import MockSyncService, get_mock_sync_service
from utils.get_current_account import get_project_or_403
from polysynergy_node_runner.services.codegen.build_executable import generate_code_from_json

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
        # CRITICAL: Data loss prevention - validate content is not empty
        if not data.content:
            raise HTTPException(
                status_code=400,
                detail="Cannot save empty content - data loss prevention"
            )

        # Check if nodes and connections are empty
        nodes = data.content.get('nodes', [])
        connections = data.content.get('connections', [])

        if len(nodes) == 0 and len(connections) == 0:
            # Allow empty ONLY for brand new setups (no previous content)
            if version.content and (version.content.get('nodes') or version.content.get('connections')):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Data loss prevention",
                        "message": f"Cannot save empty content over existing data. This would wipe the {type} clean.",
                        "previous_nodes": len(version.content.get('nodes', [])),
                        "previous_connections": len(version.content.get('connections', []))
                    }
                )

        version.content = data.content

        # Fetch project templates for Jinja extends support
        project_templates = db.query(ProjectTemplate).filter_by(project_id=project.id).all()
        templates_dict = {t.name: t.content for t in project_templates}

        version.executable = generate_code_from_json(data.content, version.id, templates=templates_dict)
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