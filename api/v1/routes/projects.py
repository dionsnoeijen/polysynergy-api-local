from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from models.project import Project
from schemas.project import ProjectCreate
import uuid

router = APIRouter()

@router.get("/")
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@router.post("/")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Project).filter(Project.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project already exists")

    project = Project(
        id=str(uuid.uuid4()),
        name=payload.name,
        tenant_id=payload.tenant_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project