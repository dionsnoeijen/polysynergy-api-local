from fastapi import APIRouter, Depends
from starlette import status

from models import Project
from repositories.stage_repository import StageRepository, get_stage_repository
from schemas.stage import StageOut, StageCreate, StageUpdate, ReorderStagesIn
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.get("/", response_model=list[StageOut])
def list_stages(
    project: Project = Depends(get_project_or_403),
    stage_repository: StageRepository = Depends(get_stage_repository),
):
    return stage_repository.get_all_by_project(project)

@router.post("/", response_model=StageOut, status_code=status.HTTP_201_CREATED)
def create_stage(
    data: StageCreate,
    project: Project = Depends(get_project_or_403),
    stage_repository: StageRepository = Depends(get_stage_repository),
):
    return stage_repository.create(data, project)

@router.get("/{stage_id}/", response_model=StageOut)
def get_stage(
    stage_id: str,
    project: Project = Depends(get_project_or_403),
    stage_repository: StageRepository = Depends(get_stage_repository),
):
    return stage_repository.get_by_id(stage_id, project)

@router.put("/{stage_id}/", response_model=StageOut)
def update_stage(
    stage_id: str,
    update: StageUpdate,
    project: Project = Depends(get_project_or_403),
    stage_repository: StageRepository = Depends(get_stage_repository),
):
    return stage_repository.update(stage_id, update, project)

@router.delete("/{stage_id}/")
def delete_stage(
    stage_id: str,
    project: Project = Depends(get_project_or_403),
    stage_repository: StageRepository = Depends(get_stage_repository),
):
    stage_repository.delete(stage_id, project)
    return {"message": "Stage deleted successfully."}

@router.post("/reorder")
def reorder_stages(
    data: ReorderStagesIn,
    project: Project = Depends(get_project_or_403),
    stage_repository: StageRepository = Depends(get_stage_repository),
):
    stage_repository.reorder(data, project)
    return {"message": "Stages reordered successfully."}
