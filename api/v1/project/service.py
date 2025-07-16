from fastapi import APIRouter, Depends, status
from typing import List

from models import Project
from repositories.service_repository import ServiceRepository, get_service_repository
from schemas.service import ServiceOut, ServiceCreateIn
from utils.get_current_account import get_project_or_403

router = APIRouter()


@router.get("/", response_model=List[ServiceOut])
def list_services(
    project: Project = Depends(get_project_or_403),
    service_repository: ServiceRepository = Depends(get_service_repository),
):
    return service_repository.get_all_by_project(project)

@router.get("/{service_id}/", response_model=ServiceOut)
def get_service(
    service_id: str,
    project: Project = Depends(get_project_or_403),
    service_repository: ServiceRepository = Depends(get_service_repository),
):
    return service_repository.get_one_with_versions_by_id(service_id, project)

@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreateIn,
    project: Project = Depends(get_project_or_403),
    blueprint_repository: ServiceRepository = Depends(get_service_repository),
):
    return blueprint_repository.create(data, project)

@router.put("/{service_id}/", response_model=ServiceOut)
def update_service(
    service_id: str,
    data: ServiceCreateIn,
    project: Project = Depends(get_project_or_403),
    service_repository: ServiceRepository = Depends(get_service_repository)
):
    return service_repository.update(service_id, data, project)


@router.delete("/{service_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: str,
    project: Project = Depends(get_project_or_403),
    blueprint_repository: ServiceRepository = Depends(get_service_repository)
):
    blueprint_repository.delete(service_id, project)
