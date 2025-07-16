from uuid import UUID

from fastapi import APIRouter, Depends, Path
from starlette import status

from models import Project
from repositories.route_repository import RouteRepository, get_route_repository
from schemas.route import RouteListOut, RouteDetailOut, RouteCreateIn
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.get("/", response_model=list[RouteListOut])
def list_routes(
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository)
):
    return route_repo.get_all_with_versions_by_project(project)

@router.post("/", response_model=RouteDetailOut, status_code=status.HTTP_201_CREATED)
def create_route(
    data: RouteCreateIn,
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    return route_repo.create(data, project)

@router.get("/{route_id}/", response_model=RouteDetailOut)
def get_route_detail(
    route_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    return route_repo.get_one_with_versions_by_id(route_id, project)

@router.patch("/{route_id}/versions/{version_id}/", response_model=RouteDetailOut)
def update_route(
    data: RouteCreateIn,
    route_id: UUID = Path(),
    version_id: UUID = Path(),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    return route_repo.update(route_id, version_id, data)

@router.delete("/{route_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: UUID,
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    route_repo.delete(route_id)
    return None