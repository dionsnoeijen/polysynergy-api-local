from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from db.session import get_db
from models import Account, Membership, Project, Stage
from schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from utils.get_current_account import get_current_account

router = APIRouter()

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_account: Account = Depends(get_current_account)
):
    memberships = db.query(Membership).filter_by(account_id=current_account.id).all()

    if not memberships:
        raise HTTPException(
            status_code=400,
            detail="No tenants available for this user"
        )

    tenant_id = memberships[0].tenant_id
    project = Project(name=project_data.name, tenant_id=tenant_id)

    db.add(project)
    db.flush()

    stage = Stage(
        project_id=project.id,
        name="mock",
        is_production=False
    )
    db.add(stage)
    db.commit()
    db.refresh(project)

    return project

@router.get("/", response_model=list[ProjectRead])
def get_projects(
    trashed: bool = Query(False),
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Membership.account_id == account.id)
    )

    if trashed:
        stmt = stmt.where(Project.deleted_at.is_not(None))
    else:
        stmt = stmt.where(Project.deleted_at.is_(None))

    projects = db.scalars(stmt).all()
    return projects

@router.get("/{project_id}/", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
        .where(Project.deleted_at.is_(None))
    )
    project = session.scalar(stmt)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return project

@router.patch("/{project_id}/", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}/", status_code=204)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    project.deleted_at = datetime.now(timezone.utc)
    db.commit()

@router.patch("/{project_id}/restore/", response_model=ProjectRead)
def restore_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
):
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    if project.deleted_at is None:
        raise HTTPException(status_code=400, detail="Project is not deleted")

    project.deleted_at = None
    db.commit()
    db.refresh(project)

    return project
