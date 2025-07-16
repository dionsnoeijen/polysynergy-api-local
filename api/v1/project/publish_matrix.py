from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import get_db
from models import Project, Route, Schedule
from schemas.publish_matrix import PublishMatrixOut
from services.publish_status import (
    get_route_publish_status,
    get_schedule_publish_status,
    get_stage_data,
)
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.get("/", response_model=PublishMatrixOut)
def get_publish_matrix(
    project: Project = Depends(get_project_or_403),
    session: Session = Depends(get_db)
):
    try:
        routes = session.execute(
            select(Route).where(Route.project_id == project.id)
        ).scalars().all()

        schedules = session.execute(
            select(Schedule).where(Schedule.project_id == project.id)
        ).scalars().all()

        print(f"Found {len(routes)} routes and {len(schedules)} schedules for project {project.id}")

        route_data = list(filter(None, (get_route_publish_status(r, session) for r in routes)))
        schedule_data = list(filter(None, (get_schedule_publish_status(s, session) for s in schedules)))
        stages = get_stage_data(str(project.id), session)

        return PublishMatrixOut(
            routes=route_data,
            schedules=schedule_data,
            stages=stages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in publish matrix: {str(e)}")