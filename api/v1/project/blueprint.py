import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID, uuid4
from typing import List

from db.project_session import get_active_project_db
from sqlalchemy.orm import Session, joinedload

from models.blueprint import Blueprint
from models.node_setup import NodeSetup
from models.node_setup_version import NodeSetupVersion
from schemas.blueprint import BlueprintOut, BlueprintIn, BlueprintMetadata
from schemas.node_setup import NodeSetupOut
from schemas.node_setup_version import NodeSetupVersionOut

router = APIRouter()

@router.get("/", response_model=List[BlueprintOut])
def list_blueprints(db: Session = Depends(get_active_project_db)):
    blueprints = db.query(Blueprint).all()
    return [
        BlueprintOut(
            id=bp.id,
            name=bp.name,
            meta=BlueprintMetadata(**(bp.meta or {})),  # wordt automatisch gemapt naar `metadata` via alias
            created_at=bp.created_at,
            updated_at=bp.updated_at,
            node_setup=None,  # vul dit later dynamisch in indien nodig
        )
        for bp in blueprints
    ]

@router.post("/", response_model=BlueprintOut, status_code=status.HTTP_201_CREATED)
def create_blueprint(
    data: BlueprintIn,
    db: Session = Depends(get_active_project_db),
):
    now = datetime.now(timezone.utc)
    blueprint_id = str(uuid4())

    # 1. Maak blueprint aan
    db_blueprint = Blueprint(
        id=blueprint_id,
        name=data.name,
        meta=data.meta.model_dump(),
        created_at=now,
        updated_at=now,
    )
    db.add(db_blueprint)

    # 2. NodeSetup aan blueprint koppelen via content_type/object_id
    node_setup_id = str(uuid4())
    node_setup = NodeSetup(
        id=node_setup_id,
        content_type="blueprint",
        object_id=blueprint_id,
        created_at=now,
        updated_at=now,
    )
    db.add(node_setup)

    # 3. Lege NodeSetupVersion toevoegen
    node_setup_version = NodeSetupVersion(
        id=str(uuid4()),
        node_setup_id=node_setup_id,
        version_number=1,
        content={},  # ← lege structuur, of default
        created_at=now,
        updated_at=now,
        published=False,
        draft=True,
    )
    db.add(node_setup_version)

    db.commit()
    db.refresh(db_blueprint)

    return BlueprintOut(
        id=db_blueprint.id,
        name=db_blueprint.name,
        meta=BlueprintMetadata(**(db_blueprint.meta or {})),
        created_at=db_blueprint.created_at,
        updated_at=db_blueprint.updated_at,
        node_setup=None,  # ← optioneel later ophalen
    )

@router.get("/{blueprint_id}/", response_model=BlueprintOut)
def get_blueprint(
    blueprint_id: str,
    db: Session = Depends(get_active_project_db)
):
    blueprint = (
        db.query(Blueprint)
        .options(joinedload(Blueprint.node_setup).joinedload(NodeSetup.versions))
        .get(blueprint_id)
    )

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    # meest recente versie ophalen
    latest_version = (
        max(blueprint.node_setup.versions, key=lambda v: v.version_number)
        if blueprint.node_setup and blueprint.node_setup.versions else None
    )

    return BlueprintOut(
        id=blueprint.id,
        name=blueprint.name,
        meta=BlueprintMetadata(**(blueprint.meta or {})),
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
        node_setup=NodeSetupOut(
            id=blueprint.node_setup.id,
            versions=[
                NodeSetupVersionOut(
                    id=v.id,
                    version_number=v.version_number,
                    content=v.content,
                    draft=v.draft,
                    published=v.published
                )
                for v in sorted(blueprint.node_setup.versions, key=lambda v: v.version_number, reverse=True)
            ]
        ) if blueprint.node_setup else None
    )
#
# @router.put("/{blueprint_id}/", response_model=BlueprintOut)
# def update_blueprint(blueprint_id: str, data: BlueprintIn, account=Depends(require_account)):
#     if blueprint_id not in blueprints_db:
#         raise HTTPException(status_code=404, detail="Blueprint not found")
#     updated = BlueprintOut(id=blueprint_id, **data.model_dump())
#     blueprints_db[blueprint_id] = updated
#     return updated
#
# @router.delete("/{blueprint_id}/", status_code=status.HTTP_204_NO_CONTENT)
# def delete_blueprint(blueprint_id: str, account=Depends(require_account)):
#     if blueprint_id in blueprints_db:
#         del blueprints_db[blueprint_id]
#     return