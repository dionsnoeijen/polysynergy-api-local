from uuid import UUID, uuid4
from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException

from db.session import get_db
from models import Schedule, NodeSetup, NodeSetupVersion, Project
from schemas.schedule import ScheduleCreateIn, ScheduleUpdateIn

class ScheduleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> List[Schedule]:
        return self.db.query(Schedule).filter(Schedule.project_id == project.id).all()

    def get_one_with_versions_by_id(self, schedule_id: UUID, project: Project) -> Schedule | None:
        schedule = self.db.query(Schedule).filter(
            Schedule.id == str(schedule_id),
            Schedule.project_id == project.id
        ).first()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="schedule",
            object_id=schedule.id
        ).first()

        schedule.node_setup = node_setup

        return schedule

    def get_by_id_or_404(self, schedule_id: UUID) -> Schedule:
        schedule = self.db.query(Schedule).filter(
            Schedule.id == str(schedule_id)
        ).first()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return schedule

    def create(self, data: ScheduleCreateIn, project: Project) -> Schedule:
        schedule = Schedule(
            id=uuid4(),
            name=data.name,
            project_id=project.id,
            cron_expression=data.cron_expression,
            start_time=data.start_time,
            end_time=data.end_time,
            is_active=data.is_active,
        )
        self.db.add(schedule)
        self.db.flush()

        node_setup = NodeSetup(id=uuid4(), content_type="schedule", object_id=schedule.id)
        self.db.add(node_setup)
        self.db.flush()

        version = NodeSetupVersion(
            id=uuid4(),
            node_setup_id=node_setup.id,
            content={},
            published=False
        )
        self.db.add(version)

        self.db.commit()
        self.db.refresh(schedule)

        schedule.node_setup = node_setup
        return schedule

    def update(self, schedule_id: UUID, data: ScheduleUpdateIn, project: Project) -> Schedule:
        schedule = self.get_one_with_versions_by_id(schedule_id, project)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(schedule, key, value)

        self.db.commit()
        self.db.refresh(schedule)

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="schedule",
            object_id=schedule.id
        ).first()

        schedule.node_setup = node_setup
        return schedule

    def delete(self, schedule_id: UUID, project: Project):
        schedule = self.get_one_with_versions_by_id(schedule_id, project)
        self.db.delete(schedule)
        self.db.commit()

def get_schedule_repository(db: Session = Depends(get_db)) -> ScheduleRepository:
    return ScheduleRepository(db)