from uuid import UUID

from fastapi import APIRouter, Depends, Path
from typing import List
from starlette import status

from models import Project
from repositories.schedule_repository import ScheduleRepository, get_schedule_repository
from schemas.schedule import ScheduleListOut, ScheduleCreateIn, ScheduleDetailOut, ScheduleUpdateIn
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.get("/", response_model=List[ScheduleListOut])
def list_schedules(
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    return schedule_repository.get_all_by_project(project)

@router.post("/", response_model=ScheduleDetailOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: ScheduleCreateIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    return schedule_repository.create(data, project)

@router.get("/{schedule_id}/", response_model=ScheduleDetailOut)
def get_schedule_detail(
    schedule_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    return schedule_repository.get_one_with_versions_by_id(schedule_id, project)

@router.patch("/{schedule_id}/", response_model=ScheduleDetailOut)
def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdateIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    return schedule_repository.update(schedule_id, data, project)

@router.delete("/{schedule_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    return schedule_repository.delete(schedule_id, project)
