from fastapi import APIRouter, Depends, status

from models import Project
from repositories.blueprint_repository import BlueprintRepository, get_blueprint_repository
from schemas.blueprint import BlueprintOut, BlueprintIn
from utils.get_current_account import get_project_or_403


router = APIRouter()

@router.get("/", response_model=list[BlueprintOut])
def list_blueprints(
    project: Project = Depends(get_project_or_403),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository)
):
    return blueprint_repository.get_all_by_project(project)

@router.post("/", response_model=BlueprintOut, status_code=status.HTTP_201_CREATED)
def create_blueprint(
    data: BlueprintIn,
    project: Project = Depends(get_project_or_403),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository)
):
    return blueprint_repository.create(data, project)

@router.get("/{blueprint_id}/", response_model=BlueprintOut)
def get_blueprint(
    blueprint_id: str,
    project: Project = Depends(get_project_or_403),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository),
):
    return blueprint_repository.get_one_with_versions_by_id(blueprint_id, project)

@router.put("/{blueprint_id}/", response_model=BlueprintOut)
def update_blueprint(
    blueprint_id: str,
    data: BlueprintIn,
    project: Project = Depends(get_project_or_403),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository)
):
    return blueprint_repository.update(blueprint_id, data, project)

@router.delete("/{blueprint_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_blueprint(
    blueprint_id: str,
    project: Project = Depends(get_project_or_403),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository)
):
    blueprint_repository.delete(blueprint_id, project)