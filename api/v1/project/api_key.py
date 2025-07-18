from uuid import UUID
from fastapi import APIRouter, Depends, Path, status

from models import Project
from schemas.api_key import ApiKeyOut, ApiKeyCreateIn, ApiKeyUpdateIn
from services.api_key_service import ApiKeyService, get_api_key_service
from utils.get_current_account import get_project_or_403

router = APIRouter()


@router.get("/", response_model=list[ApiKeyOut])
def list_api_keys(
    project: Project = Depends(get_project_or_403),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return api_key_service.list_keys(project)


@router.post("/", response_model=ApiKeyOut, status_code=status.HTTP_201_CREATED)
def create_api_key(
    data: ApiKeyCreateIn,
    project: Project = Depends(get_project_or_403),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return api_key_service.create(data, project)


@router.get("/{key_id}/", response_model=ApiKeyOut)
def get_api_key_detail(
    key_id: UUID = Path(...),
    project: Project = Depends(get_project_or_403),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return api_key_service.get_one(str(key_id), project)


@router.patch("/{key_id}/", response_model=ApiKeyOut)
def update_api_key(
    key_id: UUID,
    data: ApiKeyUpdateIn,
    project: Project = Depends(get_project_or_403),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return api_key_service.update(str(key_id), data, project)


@router.delete("/{key_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: UUID,
    project: Project = Depends(get_project_or_403),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return api_key_service.delete(str(key_id), project)


@router.patch("/assign/{route_id}/", status_code=status.HTTP_200_OK)
def assign_api_keys_to_route(
    route_id: UUID,
    api_key_refs: list[str],
    project: Project = Depends(get_project_or_403),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return api_key_service.assign_keys_to_route(str(route_id), api_key_refs, project)