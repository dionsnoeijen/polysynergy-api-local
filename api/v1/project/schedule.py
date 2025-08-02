from uuid import UUID

from models import Project, Schedule
from repositories.schedule_repository import ScheduleRepository, get_schedule_repository
from schemas.schedule import ScheduleListOut, ScheduleCreateIn, ScheduleDetailOut, ScheduleUpdateIn, \
    ScheduleUnpublishIn, SchedulePublishIn
from services.schedule_unpublish_service import ScheduleUnpublishService, get_schedule_unpublish_service
from utils.get_current_account import get_project_or_403

import logging
from fastapi import APIRouter, Depends, Path, HTTPException, status

from services.schedule_publish_service import SchedulePublishService, get_schedule_publish_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=list[ScheduleListOut])
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
    schedule_repository.delete(schedule_id, project)
    return None


@router.post("/{schedule_id}/publish/", status_code=status.HTTP_202_ACCEPTED)
def publish_schedule(
    schedule_id: UUID,
    body: SchedulePublishIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    publish_service: SchedulePublishService = Depends(get_schedule_publish_service),
):
    schedule = schedule_repository.get_one_with_versions_by_id(schedule_id, project)

    try:
        publish_service.publish(schedule, body.stage.strip())
        return {"message": "Schedule successfully published"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during schedule publish for {schedule_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during publish")

@router.post("/{schedule_id}/unpublish/", status_code=status.HTTP_202_ACCEPTED)
def unpublish_schedule(
    schedule_id: UUID,
    body: ScheduleUnpublishIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    schedule_unpublish_service: ScheduleUnpublishService = Depends(get_schedule_unpublish_service)
):
    schedule = schedule_repository.get_one_with_versions_by_id(schedule_id, project)

    try:
        schedule_unpublish_service.unpublish(schedule, body.stage.strip())
        return {"message": "Schedule unpublished successfully"}
    except Exception as e:
        logger.error(f"Error during unpublish for schedule {schedule_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during unpublish: {str(e)}"
        )

