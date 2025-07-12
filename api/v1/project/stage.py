from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from db.project_session import get_active_project_db
from models.stage import Stage
from schemas.stage import StageOut, StageCreate, StageUpdate, ReorderStagesIn

router = APIRouter()

@router.get("/", response_model=list[StageOut])
def list_stages(db: Session = Depends(get_active_project_db)):
    return db.query(Stage).all()

@router.post("/", response_model=StageOut, status_code=status.HTTP_201_CREATED)
def create_stage(
    data: StageCreate,
    db: Session = Depends(get_active_project_db)
):
    name = data.name.lower().strip()

    if name == "mock":
        raise HTTPException(status_code=400, detail="'mock' is a reserved stage name.")

    existing = db.query(Stage).filter(Stage.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stage with this name already exists.")

    if data.is_production:
        db.query(Stage).filter(Stage.is_production == True).update({Stage.is_production: False})

    max_order = db.query(func.max(Stage.order)).scalar() or 0

    stage = Stage(
        id=str(uuid4()),
        name=name,
        is_production=data.is_production,
        order=max_order + 1
    )

    db.add(stage)
    db.commit()
    db.refresh(stage)

    return stage

@router.put("/{stage_id}/", response_model=StageOut)
def update_stage(
    stage_id: str,
    update: StageUpdate,
    db: Session = Depends(get_active_project_db)
):
    stage = db.query(Stage).filter_by(id=stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    if update.name:
        new_name = update.name.lower().strip()
        if new_name == "mock":
            raise HTTPException(status_code=400, detail="'mock' is a reserved name.")
        # check uniqueness
        existing = db.query(Stage).filter(Stage.name == new_name, Stage.id != stage_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Another stage with this name already exists.")
        stage.name = new_name

    if update.is_production is True:
        db.query(Stage).update({Stage.is_production: False})
        stage.is_production = True
    elif update.is_production is False:
        stage.is_production = False

    db.commit()
    db.refresh(stage)

    return StageOut(
        id=stage.id,
        name=stage.name,
        is_production=stage.is_production,
        order=stage.order
    )

@router.delete("/{stage_id}/")
def delete_stage(stage_id: str, db: Session = Depends(get_active_project_db)):
    stage = db.query(Stage).filter(Stage.id == stage_id).first()

    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")

    if stage.name.lower() == "mock":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete reserved stage 'mock'."
        )

    db.delete(stage)
    db.commit()

    return {"message": "Stage deleted successfully."}


@router.post("/reorder")
def reorder_stages(
    data: ReorderStagesIn,
    db: Session = Depends(get_active_project_db)
):
    stages = db.query(Stage).all()
    stage_map = {str(stage.id): stage for stage in stages}

    for order, stage_id in enumerate(data.stage_ids):
        stage = stage_map.get(stage_id)
        if stage:
            stage.order = order

    db.commit()
    return {"message": "Stages reordered successfully."}
