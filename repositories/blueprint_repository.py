from uuid import uuid4, UUID
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from db.session import get_db
from models import Blueprint, NodeSetup, NodeSetupVersion, Project
from schemas.blueprint import BlueprintIn, BlueprintShareIn


class BlueprintRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> list[Blueprint]:
        blueprints = self.db.query(Blueprint).filter(Blueprint.projects.any(id=project.id)).all()

        if not blueprints:
            return []

        # Get all blueprint IDs
        blueprint_ids = [blueprint.id for blueprint in blueprints]

        # Fetch all node_setups for these blueprints in one query
        node_setups = self.db.query(NodeSetup).filter(
            NodeSetup.content_type == "blueprint",
            NodeSetup.object_id.in_(blueprint_ids)
        ).all()

        # Create a mapping of blueprint_id -> node_setup
        node_setup_map = {ns.object_id: ns for ns in node_setups}

        # Attach node_setup to each blueprint
        for blueprint in blueprints:
            blueprint.node_setup = node_setup_map.get(blueprint.id)

        return blueprints

    def get_one_with_versions_by_id(self, blueprint_id: str, project: Project) -> Blueprint:
        blueprint = (
            self.db.query(Blueprint)
            .filter(
                Blueprint.id == blueprint_id,
                Blueprint.projects.any(id=project.id)
            )
            .first()
        )

        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="blueprint",
            object_id=blueprint.id
        ).first()

        blueprint.node_setup = node_setup  # ad-hoc attribuut, net als bij Route

        return blueprint

    def create(self, data: BlueprintIn, project: Project) -> Blueprint:
        now = datetime.now(timezone.utc)
        blueprint_id = uuid4()

        blueprint = Blueprint(
            id=blueprint_id,
            name=data.name,
            meta=data.meta.model_dump(),
            created_at=now,
            updated_at=now,
            tenant_id=project.tenant_id,
            projects=[project],
        )
        self.db.add(blueprint)

        node_setup_id = uuid4()
        node_setup = NodeSetup(
            id=node_setup_id,
            content_type="blueprint",
            object_id=blueprint_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(node_setup)

        version = NodeSetupVersion(
            id=uuid4(),
            node_setup_id=node_setup_id,
            version_number=1,
            content={},
            created_at=now,
            updated_at=now,
            draft=True,
        )
        self.db.add(version)

        self.db.commit()
        self.db.refresh(blueprint)

        blueprint.node_setup = node_setup
        return blueprint

    def update(self, blueprint_id: str, data: BlueprintIn, project: Project) -> Blueprint:
        blueprint = self.get_one_with_versions_by_id(blueprint_id, project)

        blueprint.name = data.name
        blueprint.meta = data.meta.model_dump()
        blueprint.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(blueprint)
        return blueprint

    def delete(self, blueprint_id: str, project: Project):
        blueprint = self.get_one_with_versions_by_id(blueprint_id, project)
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="blueprint",
            object_id=blueprint.id
        ).first()

        if node_setup:
            self.db.delete(node_setup)

        self.db.delete(blueprint)
        self.db.commit()

def get_blueprint_repository(db: Session=Depends(get_db)):
    return BlueprintRepository(db)
