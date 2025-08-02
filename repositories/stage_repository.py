from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.session import get_db
from models import Stage, Project
from schemas.stage import StageCreate, StageUpdate, ReorderStagesIn


class StageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> list[Stage]:
        return self.db.query(Stage).filter(Stage.project_id == project.id).order_by(Stage.order).all()

    def get_by_id(self, stage_id: str, project: Project) -> Stage:
        stage = (
            self.db.query(Stage)
            .filter(Stage.id == stage_id, Stage.project_id == project.id)
            .first()
        )
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
        return stage

    def create(self, data: StageCreate, project: Project) -> Stage:
        name = data.name.lower().strip()

        if name == "mock":
            raise HTTPException(status_code=400, detail="'mock' is a reserved stage name.")

        # Check for existing stage with same name in project
        existing = (
            self.db.query(Stage)
            .filter(Stage.name == name, Stage.project_id == project.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Stage with this name already exists.")

        # If setting as production, remove production flag from other stages in project
        if data.is_production:
            self.db.query(Stage).filter(
                Stage.is_production == True, 
                Stage.project_id == project.id
            ).update({Stage.is_production: False})

        # Get max order for this project
        max_order = (
            self.db.query(func.max(Stage.order))
            .filter(Stage.project_id == project.id)
            .scalar() or 0
        )

        stage = Stage(
            id=str(uuid4()),
            name=name,
            is_production=data.is_production,
            order=max_order + 1,
            project_id=project.id,
        )

        self.db.add(stage)
        self.db.commit()
        self.db.refresh(stage)

        return stage

    def update(self, stage_id: str, data: StageUpdate, project: Project) -> Stage:
        stage = self.get_by_id(stage_id, project)

        if data.name:
            new_name = data.name.lower().strip()
            if new_name == "mock":
                raise HTTPException(status_code=400, detail="'mock' is a reserved name.")
            
            # Check uniqueness within project
            existing = (
                self.db.query(Stage)
                .filter(
                    Stage.name == new_name, 
                    Stage.id != stage_id, 
                    Stage.project_id == project.id
                )
                .first()
            )
            if existing:
                raise HTTPException(status_code=400, detail="Another stage with this name already exists.")
            
            stage.name = new_name

        if data.is_production is True:
            # Remove production flag from other stages in project
            self.db.query(Stage).filter(
                Stage.project_id == project.id
            ).update({Stage.is_production: False})
            stage.is_production = True
        elif data.is_production is False:
            stage.is_production = False

        stage.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(stage)

        return stage

    def delete(self, stage_id: str, project: Project) -> None:
        stage = self.get_by_id(stage_id, project)

        if stage.name.lower() == "mock":
            raise HTTPException(
                status_code=400,
                detail="Cannot delete reserved stage 'mock'."
            )

        self.db.delete(stage)
        self.db.commit()

    def reorder(self, data: ReorderStagesIn, project: Project) -> None:
        stages = self.db.query(Stage).filter(Stage.project_id == project.id).all()
        stage_map = {str(stage.id): stage for stage in stages}

        for order, stage_id in enumerate(data.stage_ids):
            stage = stage_map.get(stage_id)
            if stage:
                stage.order = order
                stage.updated_at = datetime.now(timezone.utc)

        self.db.commit()


def get_stage_repository(db: Session = Depends(get_db)) -> StageRepository:
    return StageRepository(db)