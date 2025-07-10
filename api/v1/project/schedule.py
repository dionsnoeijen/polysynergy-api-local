from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List

from starlette import status

from db.project_session import get_active_project_db
from models_project import NodeSetup, NodeSetupVersion
from models_project.schedule import Schedule
from schemas.schedule import ScheduleListOut, ScheduleCreateIn, ScheduleDetailOut, ScheduleUpdateIn

router = APIRouter()

@router.get("/", response_model=List[ScheduleListOut])
def list_schedules(
    db: Session = Depends(get_active_project_db)
):
    schedules = db.query(Schedule).all()
    if not schedules:
        return []
    return schedules

@router.post("/", response_model=ScheduleDetailOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: ScheduleCreateIn,
    db: Session = Depends(get_active_project_db),
):
    # Maak Schedule aan
    schedule = Schedule(
        id=str(uuid4()),
        name=data.name,
        cron_expression=data.cron_expression,
        start_time=data.start_time,
        end_time=data.end_time,
        is_active=data.is_active,
    )
    db.add(schedule)
    db.flush()

    node_setup = NodeSetup(
        id=str(uuid4()),
        content_type="schedule",
        object_id=schedule.id,
    )
    db.add(node_setup)
    db.flush()

    version = NodeSetupVersion(
        id=str(uuid4()),
        node_setup_id=node_setup.id,
        version_number=1,
        content={},
    )
    db.add(version)

    db.commit()
    db.refresh(schedule)

    return schedule

@router.get("/{schedule_id}/", response_model=ScheduleDetailOut)
def get_schedule_detail(
    schedule_id: UUID = Path(...),
    db: Session = Depends(get_active_project_db)
):
    schedule = db.query(Schedule).filter(Schedule.id == str(schedule_id)).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    node_setup = db.query(NodeSetup).filter_by(
        content_type="schedule",
        object_id=schedule.id
    ).first()

    schedule.node_setup = node_setup
    return schedule

@router.patch("/{schedule_id}/", response_model=ScheduleDetailOut)
def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdateIn,
    db: Session = Depends(get_active_project_db),
):
    schedule = db.query(Schedule).filter(Schedule.id == str(schedule_id)).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)

    db.commit()
    db.refresh(schedule)

    node_setup = db.query(NodeSetup).filter_by(
        content_type="schedule",
        object_id=schedule.id
    ).first()

    schedule.node_setup = node_setup
    return schedule

@router.delete("/{schedule_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_active_project_db),
):
    schedule = db.query(Schedule).filter(Schedule.id == str(schedule_id)).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # TODO: Unpublish alle gekoppelde versies (voor nu als placeholder)
    # ScheduleUnpublishService.unpublish(schedule)

    db.delete(schedule)
    db.commit()
