import logging
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException

from db.session import get_db
from models import Route, RouteSegment, NodeSetup, NodeSetupVersion, Project
from schemas.route import RouteCreateIn
from models.route import Method

logger = logging.getLogger(__name__)


class RouteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> list[Route]:
        return self.db.query(Route).filter(Route.project_id == project.id).all()

    def get_by_id(self, route_id: UUID, project: Project) -> Route | None:
        return self.db.query(Route).filter(
            Route.id == str(route_id),
            Route.project_id == project.id
        ).first()

    def get_all_with_versions_by_project(self, project: Project) -> list[Route]:
        routes = self.db.query(Route).filter(Route.project_id == project.id).all()

        for route in routes:
            node_setup = self.db.query(NodeSetup).filter_by(
                content_type="route", object_id=str(route.id)
            ).first()
            route.node_setup = node_setup if node_setup else []
        return routes

    def get_one_with_versions_by_id(self, route_id: UUID, project: Project) -> Route | None:
        route = self.db.query(Route).filter(
            Route.id == str(route_id),
            Project.id == project.id
        ).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="route", object_id=str(route.id)
        ).first()
        route.node_setup = node_setup if node_setup else []
        return route

    def exists_with_pattern(self, method: str, project: Project, normalized_pattern: list[str]) -> bool:
        routes = self.db.query(Route).filter(
            Route.method == method,
            Route.project_id == project.id
        ).all()

        for route in routes:
            segments = route.segments or []
            pattern = [
                "{var}" if seg.type == "variable" else seg.name
                for seg in segments
            ]
            if pattern == normalized_pattern:
                return True
        return False

    def create(self, data: RouteCreateIn, project: Project) -> Route:
        def normalize_segments(segments):
            return [
                "{var}" if seg.type == "variable" else seg.name
                for seg in segments
            ] if segments else []

        new_pattern = normalize_segments(data.segments)

        existing_routes = self.db.query(Route).filter(
            Route.method == data.method,
            Route.project_id == project.id
        ).all()

        for existing in existing_routes:
            existing_pattern = normalize_segments(existing.segments or [])
            if existing_pattern == new_pattern:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate route with the same structure is not allowed."
                )

        # Route
        route = Route(
            id=uuid4(),
            project_id=project.id,
            description=data.description,
            method=Method(data.method)
        )
        self.db.add(route)
        self.db.flush()

        # Segments
        for segment in data.segments:
            seg = RouteSegment(
                id=uuid4(),
                route_id=route.id,
                **segment.model_dump(mode="json")
            )
            self.db.add(seg)

        # NodeSetup + versie
        node_setup = NodeSetup(id=uuid4(), content_type="route", object_id=route.id)
        self.db.add(node_setup)
        self.db.flush()

        version = NodeSetupVersion(
            id=uuid4(),
            node_setup_id=node_setup.id,
            content={}
        )
        self.db.add(version)

        self.db.commit()
        self.db.refresh(route)
        return route

    def update(self, route_id: UUID, version_id: UUID, data: RouteCreateIn) -> Route:
        route = self.get_by_id_or_404(route_id)
        route.description = data.description
        route.method = data.method

        # Segments vervangen
        route.segments.clear()
        for segment in data.segments:
            seg = RouteSegment(id=uuid4(), route_id=route.id, **segment.model_dump(mode="json"))
            self.db.add(seg)

        version = self.db.query(NodeSetupVersion).filter_by(id=str(version_id)).first()
        if not version:
            raise HTTPException(status_code=404, detail="NodeSetupVersion not found")


        self.db.commit()
        self.db.refresh(route)
        return route

    def delete(self, route_id: UUID, project: Project) -> None:
        route = self.get_by_id(route_id, project)
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Also delete the associated NodeSetup record
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="route", 
            object_id=str(route_id)
        ).first()
        if node_setup:
            self.db.delete(node_setup)
        
        self.db.delete(route)
        self.db.commit()

    def get_node_setup(self, route_id: UUID) -> NodeSetup | None:
        return self.db.query(NodeSetup).filter_by(content_type="route", object_id=str(route_id)).first()

    def get_by_id_or_404(self, route_id: UUID) -> Route:
        route = (
            self.db.query(Route)
            .filter_by(id=str(route_id)).first()
        )
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        return route

def get_route_repository(db: Session = Depends(get_db)) -> RouteRepository:
    return RouteRepository(db)
