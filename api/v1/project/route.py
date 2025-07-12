from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from starlette import status

from db.project_session import get_active_project_db
from models import RouteSegment, NodeSetupVersion
from models.route import Route, Method
from models.node_setup import NodeSetup
from schemas.route import RouteListOut, RouteDetailOut, RouteCreateIn

router = APIRouter()

@router.get("/", response_model=list[RouteListOut])
def list_dynamic_routes(
    db: Session = Depends(get_active_project_db)
):
    routes = db.query(Route).all()

    for route in routes:
        try:
            node_setup = db.query(NodeSetup).filter_by(
                content_type="route",
                object_id=str(route.id)
            ).first()
            route.versions = node_setup.versions if node_setup else []
        except Exception:
            route.versions = []

    return routes

@router.post("/", response_model=RouteDetailOut, status_code=status.HTTP_201_CREATED)
def create_dynamic_route(
    data: RouteCreateIn,
    db: Session = Depends(get_active_project_db)
):
    def normalize_segments(segments):
        return [
            "{var}" if seg.type == "variable" else seg.name
            for seg in segments
        ]

    new_pattern = normalize_segments(data.segments)

    existing_routes = db.query(Route).filter(Route.method == data.method).all()

    for existing in existing_routes:
        existing_segments = existing.segments or []
        existing_pattern = normalize_segments(existing_segments)

        if existing_pattern == new_pattern:
            raise HTTPException(
                status_code=400,
                detail="Duplicate route with the same structure is not allowed."
            )

    # Maak route aan
    route = Route(
        id=str(uuid4()),
        description=data.description,
        method=Method(data.method),
    )
    db.add(route)
    db.flush()

    # Segments aanmaken
    for segment in data.segments:
        seg = RouteSegment(
            id=str(uuid4()),
            route_id=route.id,
            **segment.model_dump(mode="json")
        )
        db.add(seg)

    # NodeSetup + versie
    node_setup = NodeSetup(
        id=str(uuid4()),
        content_type="route",
        object_id=route.id
    )
    db.add(node_setup)
    db.flush()

    version = NodeSetupVersion(
        id=str(uuid4()),
        node_setup_id=node_setup.id,
        content={},
        published=False
    )
    db.add(version)

    db.commit()
    db.refresh(route)
    return route

@router.get("/{route_id}/", response_model=RouteDetailOut)
def get_dynamic_route_detail(
    route_id: UUID = Path(...),
    db: Session = Depends(get_active_project_db)
):
    route = db.query(Route).filter(Route.id == str(route_id)).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    try:
        node_setup = db.query(NodeSetup).filter_by(
            content_type="route",
            object_id=str(route.id)
        ).first()
        route.node_setup = node_setup
    except Exception:
        route.node_setup = None

    return route

@router.patch("/{route_id}/versions/{version_id}/", response_model=RouteDetailOut)
def update_dynamic_route(
    route_id: UUID,
    version_id: UUID,
    data: RouteCreateIn,
    db: Session = Depends(get_active_project_db),
):
    route = db.query(Route).filter(Route.id == str(route_id)).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.description = data.description
    route.method = data.method

    route.segments.clear()
    for segment in data.segments:
        db_segment = RouteSegment(
            id=str(uuid4()),
            route_id=route.id,
            **segment.model_dump(mode="json")
        )
        db.add(db_segment)

    version = db.query(NodeSetupVersion).filter(NodeSetupVersion.id == str(version_id)).first()
    if not version:
        raise HTTPException(status_code=404, detail="NodeSetupVersion not found")

    # TODO: RoutePublishService.updateRoute(route, version, stage="mock")

    db.commit()
    db.refresh(route)
    return route

@router.delete("/{route_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_dynamic_route(
    route_id: UUID,
    db: Session = Depends(get_active_project_db),
):
    route = db.query(Route).filter(Route.id == str(route_id)).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # TODO: RouteDeleteService.unpublish_all(route)

    db.delete(route)
    db.commit()
    return None