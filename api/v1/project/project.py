from uuid import UUID

from fastapi import APIRouter, Depends, status, Query

from models import Account
from repositories.project_repository import ProjectRepository, get_project_repository
from schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from utils.get_current_account import get_current_account

router = APIRouter()

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    project_repo: ProjectRepository = Depends(get_project_repository),
    current_account: Account = Depends(get_current_account)
):
    return project_repo.create(project_data, current_account)

@router.get("/", response_model=list[ProjectRead])
def get_projects(
    trashed: bool = Query(False),
    project_repo: ProjectRepository = Depends(get_project_repository),
    account: Account = Depends(get_current_account),
):
    return project_repo.get_all_by_account(account, include_trashed=trashed)

@router.get("/{project_id}/", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repository),
    account: Account = Depends(get_current_account),
):
    return project_repo.get_or_404(project_id, account)

@router.patch("/{project_id}/", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    project_repo: ProjectRepository = Depends(get_project_repository),
    account: Account = Depends(get_current_account),
):
    project = project_repo.get_for_update_or_404(project_id, account)
    update_data = data.model_dump(exclude_unset=True)
    return project_repo.update(project, update_data)

@router.delete("/{project_id}/", status_code=204)
def delete_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repository),
    account: Account = Depends(get_current_account),
):
    project = project_repo.get_for_update_or_404(project_id, account)
    project_repo.soft_delete(project)

@router.patch("/{project_id}/restore/", response_model=ProjectRead)
def restore_project(
    project_id: UUID,
    project_repo: ProjectRepository = Depends(get_project_repository),
    account: Account = Depends(get_current_account),
):
    project = project_repo.get_for_update_or_404(project_id, account)
    return project_repo.restore(project)
