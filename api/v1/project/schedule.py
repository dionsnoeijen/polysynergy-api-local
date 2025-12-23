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
from core.settings import settings

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

@router.get("/local-jobs/", status_code=status.HTTP_200_OK)
async def get_local_scheduled_jobs(
    project: Project = Depends(get_project_or_403),
):
    """
    Get all currently active scheduled jobs in the local scheduler.
    Only available when EXECUTE_NODE_SETUP_LOCAL is enabled.
    """
    if not settings.EXECUTE_NODE_SETUP_LOCAL:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local schedule execution is not enabled"
        )

    try:
        # Import here to avoid circular imports
        from services.local_schedule_service import get_local_schedule_service

        local_service = get_local_schedule_service()

        if not local_service.is_running():
            return {
                "active_jobs": [],
                "scheduler_status": "stopped",
                "message": "Local scheduler is not running"
            }

        active_jobs = local_service.get_active_jobs()

        return {
            "active_jobs": active_jobs,
            "scheduler_status": "running",
            "total_jobs": len(active_jobs)
        }

    except Exception as e:
        logger.error(f"Error getting local scheduled jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving local scheduled jobs: {str(e)}"
        )

@router.get("/{schedule_id}/", response_model=ScheduleDetailOut)
def get_schedule_detail(
    schedule_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    return schedule_repository.get_one_with_versions_by_id(schedule_id, project)

@router.patch("/{schedule_id}/", response_model=ScheduleDetailOut)
async def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdateIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    # Update in database first
    updated_schedule = schedule_repository.update(schedule_id, data, project)

    # If local execution is enabled, also update the schedule in APScheduler
    if settings.EXECUTE_NODE_SETUP_LOCAL:
        try:
            from services.local_schedule_service import get_local_schedule_service
            from models import NodeSetup, NodeSetupVersion, NodeSetupVersionStage, Stage
            from db.session import get_db

            local_service = get_local_schedule_service()

            # Check if this schedule is currently published to any stage
            db = next(get_db())
            try:
                node_setup = db.query(NodeSetup).filter_by(
                    content_type="schedule",
                    object_id=schedule_id
                ).first()

                if node_setup:
                    # Get all stage links for this schedule
                    stage_links = db.query(NodeSetupVersionStage).filter_by(
                        node_setup_id=node_setup.id
                    ).all()

                    if stage_links:
                        # Get the latest version with executable code
                        version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
                        node_setup_version = version[0] if version else None

                        if node_setup_version and node_setup_version.executable:
                            # For each published stage, update the schedule in APScheduler
                            for stage_link in stage_links:
                                stage_obj = db.query(Stage).filter_by(id=stage_link.stage_id).first()
                                if not stage_obj:
                                    continue

                                # If schedule is now inactive, remove it from APScheduler
                                if data.is_active is False:
                                    await local_service.remove_schedule(str(schedule_id))
                                    logger.info(f"Removed inactive schedule {schedule_id} from local scheduler")
                                else:
                                    # Update the schedule in APScheduler by removing and re-adding
                                    schedule_data = {
                                        'id': updated_schedule.id,
                                        'name': updated_schedule.name,
                                        'project_id': updated_schedule.project_id,
                                        'tenant_id': project.tenant_id,
                                        'cron_expression': updated_schedule.cron_expression,
                                        'stage': stage_obj.name
                                    }

                                    # Remove old schedule
                                    await local_service.remove_schedule(str(schedule_id))

                                    # Add updated schedule
                                    success = await local_service.add_schedule_with_code(
                                        schedule_data,
                                        node_setup_version.executable
                                    )

                                    if success:
                                        logger.info(f"Updated schedule {schedule_id} in local scheduler for stage {stage_obj.name}")
                                    else:
                                        logger.warning(f"Failed to update schedule {schedule_id} in local scheduler")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error updating schedule in local scheduler: {str(e)}", exc_info=True)
            # Don't fail the entire request if local scheduler update fails
            # The database update already succeeded

    return updated_schedule

@router.delete("/{schedule_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
):
    schedule_repository.delete(schedule_id, project)
    return None


@router.post("/{schedule_id}/publish/", status_code=status.HTTP_202_ACCEPTED)
async def publish_schedule(
    schedule_id: UUID,
    body: SchedulePublishIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    publish_service: SchedulePublishService = Depends(get_schedule_publish_service),
):
    schedule = schedule_repository.get_one_with_versions_by_id(schedule_id, project)

    try:
        # Use local schedule service when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            # Import here to avoid circular imports
            from services.local_schedule_service import get_local_schedule_service
            from models import NodeSetup, NodeSetupVersion
            from db.session import get_db

            # Get the executable code like in regular publish service
            db = next(get_db())
            try:
                node_setup = db.query(NodeSetup).filter_by(
                    content_type="schedule",
                    object_id=schedule.id
                ).first()

                if not node_setup:
                    raise HTTPException(status_code=404, detail="NodeSetup not found for this schedule.")

                version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
                node_setup_version = version[0] if version else None

                if not node_setup_version or not node_setup_version.executable:
                    raise HTTPException(status_code=400, detail="No executable code found for this schedule.")

                if not schedule.cron_expression:
                    raise HTTPException(status_code=400, detail="No cron expression defined")

                # Store necessary data to avoid SQLAlchemy session issues
                schedule_data = {
                    'id': schedule.id,
                    'name': schedule.name,
                    'project_id': schedule.project_id,
                    'tenant_id': project.tenant_id,
                    'cron_expression': schedule.cron_expression,
                    'stage': body.stage.strip()
                }

                local_service = get_local_schedule_service()
                success = await local_service.add_schedule_with_code(
                    schedule_data,
                    node_setup_version.executable
                )

                if success:
                    # Create NodeSetupVersionStage record to update publish matrix
                    from models import Stage, NodeSetupVersionStage

                    stage_obj = db.query(Stage).filter_by(
                        project=project, name=body.stage.strip()
                    ).first()

                    if stage_obj:
                        # Create or update the stage link
                        db.merge(NodeSetupVersionStage(
                            stage_id=stage_obj.id,
                            node_setup_id=node_setup.id,
                            version_id=node_setup_version.id,
                            executable_hash=node_setup_version.executable_hash
                        ))
                        db.commit()
                        logger.debug(f"Created NodeSetupVersionStage link for schedule {schedule.id} and stage {body.stage.strip()}")
                    else:
                        logger.warning(f"Stage '{body.stage.strip()}' not found for project {project.id}")

                    return {"message": "Schedule successfully published locally"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to publish schedule locally")
            finally:
                db.close()
        else:
            # Use Lambda for production or when local execution is disabled
            publish_service.publish(schedule, body.stage.strip())
            return {"message": "Schedule successfully published"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during schedule publish for {schedule_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during publish")

@router.post("/{schedule_id}/unpublish/", status_code=status.HTTP_202_ACCEPTED)
async def unpublish_schedule(
    schedule_id: UUID,
    body: ScheduleUnpublishIn,
    project: Project = Depends(get_project_or_403),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    schedule_unpublish_service: ScheduleUnpublishService = Depends(get_schedule_unpublish_service)
):
    schedule = schedule_repository.get_one_with_versions_by_id(schedule_id, project)

    try:
        # Use local schedule service when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            # Import here to avoid circular imports
            from services.local_schedule_service import get_local_schedule_service
            from models import Stage, NodeSetupVersionStage
            from db.session import get_db as get_database_session

            local_service = get_local_schedule_service()
            success = await local_service.remove_schedule(str(schedule_id))

            # Remove NodeSetupVersionStage record to update publish matrix
            db = next(get_database_session())
            try:
                stage_obj = db.query(Stage).filter_by(
                    project=project, name=body.stage.strip()
                ).first()

                if stage_obj:
                    deleted = db.query(NodeSetupVersionStage).filter(
                        NodeSetupVersionStage.stage_id == stage_obj.id,
                        NodeSetupVersionStage.node_setup.has(content_type="schedule", object_id=schedule_id)
                    ).delete()
                    db.commit()
                    logger.debug(f"Deleted {deleted} NodeSetupVersionStage link(s) for schedule {schedule_id}")
            finally:
                db.close()

            if success:
                return {"message": "Schedule unpublished locally"}
            else:
                return {"message": "Schedule not found in local scheduler or already unpublished"}
        else:
            # Use Lambda for production
            schedule_unpublish_service.unpublish(schedule, body.stage.strip())
            return {"message": "Schedule unpublished successfully"}
    except Exception as e:
        logger.error(f"Error during unpublish for schedule {schedule_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during unpublish: {str(e)}"
        )

