from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException

from db.session import get_db
from models import Service, Project, NodeSetup, NodeSetupVersion
from schemas.service import ServiceCreateIn


class ServiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> list[Service]:
        services = self.db.query(Service).filter(Service.projects.any(id=project.id)).all()

        if not services:
            return []

        # Get all service IDs
        service_ids = [service.id for service in services]

        # Fetch all node_setups for these services in one query
        node_setups = self.db.query(NodeSetup).filter(
            NodeSetup.content_type == "service",
            NodeSetup.object_id.in_(service_ids)
        ).all()

        # Create a mapping of service_id -> node_setup
        node_setup_map = {ns.object_id: ns for ns in node_setups}

        # Attach node_setup to each service
        for service in services:
            service.node_setup = node_setup_map.get(service.id)

        return services

    def get_one_with_versions_by_id(self, service_id: str, project: Project) -> Service:
        service = (
            self.db.query(Service)
            .filter(Service.id == service_id, Service.projects.any(id=project.id))
            .first()
        )

        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="service",
            object_id=service.id
        ).first()

        service.node_setup = node_setup
        return service

    def create(self, data: ServiceCreateIn, project: Project) -> Service:
        service_id = uuid4()
        service = Service(
            id=service_id,
            name=data.name,
            meta=data.meta.model_dump(),
            tenant_id=project.tenant_id,
            projects=[project],
        )
        self.db.add(service)
        self.db.flush()

        node_setup_id = uuid4()
        node_setup = NodeSetup(
            id=node_setup_id,
            content_type="service",
            object_id=service.id,
        )
        self.db.add(node_setup)
        self.db.flush()

        version = NodeSetupVersion(
            id=uuid4(),
            node_setup_id=node_setup.id,
            version_number=1,
            content=data.node_setup_content or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            draft=True,
        )
        self.db.add(version)

        self.db.commit()
        self.db.refresh(service)
        service.node_setup = node_setup

        return service

    def update(self, service_id: str, data: ServiceCreateIn, project: Project) -> Service:
        service = self.get_one_with_versions_by_id(service_id, project)

        service.name = data.name
        service.meta = data.meta.model_dump()

        if data.node_setup_content:
            version = (
                self.db.query(NodeSetupVersion)
                .join(NodeSetup)
                .filter(
                    NodeSetup.content_type == "service",
                    NodeSetup.object_id == service.id,
                    NodeSetupVersion.version_number == 1
                )
                .first()
            )
            if version:
                version.content = data.node_setup_content

        self.db.commit()
        self.db.refresh(service)
        return service

    def delete(self, service_id: str, project: Project):
        service = self.get_one_with_versions_by_id(service_id, project)

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="service",
            object_id=service.id
        ).first()

        if node_setup:
            self.db.delete(node_setup)

        self.db.delete(service)
        self.db.commit()


def get_service_repository(db: Session = Depends(get_db)) -> ServiceRepository:
    return ServiceRepository(db)